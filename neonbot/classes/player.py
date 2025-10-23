from __future__ import annotations

import asyncio
import json
import os
import random
from os import path
from typing import Dict, List, Optional, Union

import discord
from discord.ext import commands, tasks
from discord.utils import MISSING
from i18n import t

from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.classes.player_controls import PlayerControls
from neonbot.classes.ytdl import Ytdl
from neonbot.classes.ytmusic import YTMusic
from neonbot.enums import PlayerState, Repeat
from neonbot.models.guild import GuildModel
from neonbot.utils import log
from neonbot.utils.constants import FFMPEG_BEFORE_OPTIONS, FFMPEG_OPTIONS, ICONS, PLAYER_CACHE_PATH
from neonbot.utils.exceptions import ApiError, PlayerError, YtdlError
from neonbot.utils.functions import remove_ansi


class Player:
    servers: dict[int, Player] = {}

    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self.loop = asyncio.get_event_loop()
        self.settings = GuildModel.get_instance(ctx.guild.id)
        self.player_controls = PlayerControls(self)

        self.queue = []
        self.current_track = 0
        self.track_list = [0]
        self.shuffled_list = []
        self.messages: Dict[str, Optional[discord.Message]] = dict(
            playing=None,
            finished=None,
        )
        self.last_track = None
        self.last_voice_channel: Optional[discord.VoiceChannel] = None
        self.state = PlayerState.NONE
        self.jump_to_track = None

    @property
    def channel(self):
        return self.ctx.channel

    @property
    def connection(self) -> Optional[discord.VoiceClient]:
        return self.ctx.voice_client

    @staticmethod
    async def get_instance(origin: Union[discord.Interaction, discord.Message]) -> Player:
        guild_id = origin.guild.id

        if guild_id not in Player.servers.keys():
            ctx = await bot.get_context(origin)
            Player.servers[guild_id] = Player(ctx)

        return Player.servers[guild_id]

    @staticmethod
    def get_instance_from_guild(guild: discord.Guild) -> Optional[Player]:
        return Player.servers.get(guild.id)

    def remove_instance(self) -> None:
        guild_id = self.ctx.guild.id

        if guild_id in Player.servers.keys():
            del Player.servers[guild_id]

    @property
    def repeat(self) -> int:
        return self.settings.music.repeat

    @property
    def shuffle(self) -> bool:
        return self.settings.music.shuffle

    @property
    def autoplay(self) -> bool:
        return self.settings.music.autoplay

    @repeat.setter
    def repeat(self, value) -> None:
        self.settings.music.repeat = value
        self.loop.create_task(self.settings.save_changes())

    @shuffle.setter
    def shuffle(self, value) -> None:
        self.settings.music.shuffle = value
        self.loop.create_task(self.settings.save_changes())

    @autoplay.setter
    def autoplay(self, value) -> None:
        self.settings.music.autoplay = value
        self.loop.create_task(self.settings.save_changes())

    @property
    def is_last_track(self):
        return self.track_list[self.current_track] == len(self.queue) - 1

    @property
    def now_playing(self) -> Union[dict, None]:
        try:
            return {**self.queue[self.track_list[self.current_track]], 'index': self.track_list[self.current_track] + 1}
        except IndexError:
            return None

    @now_playing.setter
    def now_playing(self, value) -> None:
        try:
            self.queue[self.track_list[self.current_track]] = value
        except IndexError:
            pass

    def get_track(self, index: int) -> dict:
        return self.queue[index]

    @tasks.loop(count=1)
    async def reset_timeout(self, timeout=60) -> None:
        await asyncio.sleep(timeout)

        await self.reset()

        msg = 'Player reset due to inactivity.'
        log.cmd(self.ctx, msg)
        await self.channel.send(embed=Embed(msg))

        self.remove_instance()

    async def connect(self, channel: Optional[discord.VoiceChannel] = None):
        if self.connection:
            return

        if not channel and self.last_voice_channel:
            await self.last_voice_channel.connect(self_deaf=True)
        else:
            self.last_voice_channel = channel
            await channel.connect(self_deaf=True)

        log.cmd(self.ctx, t('music.player_connected', channel=self.last_voice_channel))

    async def disconnect(self, force=True, timeout=None) -> None:
        if self.connection and self.connection.is_connected():
            try:
                await asyncio.wait_for(self.connection.disconnect(force=force), timeout=timeout)
            except asyncio.TimeoutError:
                pass

    async def set_repeat(self, mode: Repeat, requester: discord.User):
        self.repeat = mode.value

        msg = t('music.repeat_changed', mode=mode.name.lower(), user=requester.mention)
        await self.channel.send(embed=Embed(msg))
        log.cmd(self.ctx, msg, user=requester)

        await self.refresh_player_message(embed=True)

    async def set_shuffle(self, requester: discord.User):
        self.shuffle = not self.shuffle

        msg = t('music.shuffle_changed', mode='on' if self.shuffle else 'off', user=requester.mention)
        await self.channel.send(embed=Embed(msg))
        log.cmd(self.ctx, msg, user=requester)

        await self.refresh_player_message(embed=True)

    async def set_autoplay(self, requester: discord.User):
        self.autoplay = not self.autoplay

        msg = t('music.autoplay_changed', mode='on' if self.autoplay else 'off', user=requester.mention)
        await self.channel.send(embed=Embed(msg))
        log.cmd(self.ctx, msg, user=requester)

        await self.refresh_player_message(embed=True)

    async def pause(self, requester: discord.User, auto=False):
        if self.connection.is_paused() or not self.connection.is_playing():
            return

        self.connection.pause()
        log.cmd(self.ctx, t('music.player_paused', user=requester.name))

        self.state = PlayerState.AUTO_PAUSED if auto else PlayerState.PAUSED

        await self.channel.send(embed=Embed(t('music.player_paused', user=requester.mention)))
        await self.refresh_player_message()

    async def resume(self, requester: discord.User):
        if not self.connection.is_paused():
            return

        self.connection.resume()
        log.cmd(self.ctx, t('music.player_resumed', user=requester.name))

        self.state = PlayerState.PLAYING

        await self.channel.send(embed=Embed(t('music.player_resumed', user=requester.mention)))
        await self.refresh_player_message()

    async def play(self) -> None:
        if not self.connection or not self.connection.is_connected() or self.connection.is_playing():
            return

        try:
            if not self.now_playing.get('stream') or Ytdl.is_expired(self.now_playing['stream']):
                ytdl_info = await Ytdl().extract_info(self.now_playing['url'], download=True)
                info = ytdl_info.get_track()
                self.now_playing = {'index': self.track_list[self.current_track] + 1, **self.now_playing, **info}

            source = discord.FFmpegOpusAudio(
                self.now_playing['stream'],
                # before_options=None if not self.now_playing['is_live'] else FFMPEG_BEFORE_OPTIONS,
                before_options=FFMPEG_BEFORE_OPTIONS,
                options=FFMPEG_OPTIONS,
            )
            self.connection.play(source, after=lambda e: self.loop.create_task(self.after(error=e)))
            self.state = PlayerState.PLAYING
            await self.send_playing_message()

        except Exception as error:
            msg = str(error)

            if isinstance(error, discord.ClientException):
                if str(error) == 'Already playing audio.':
                    return
            elif not isinstance(error, YtdlError):
                msg = t('music.player_error')

            log.exception(msg, error)
            await self.channel.send(embed=Embed(remove_ansi(msg)).set_author(self.now_playing.get('title')))
            self.loop.create_task(self.after())

    async def after(self, error=None):
        if error:
            log.error(error)
            return

        self.last_track = self.now_playing

        if self.state == PlayerState.NONE:
            return

        if self.state == PlayerState.STOPPED:
            await self.send_finished_message(detailed=True)
            return

        if self.state == PlayerState.JUMPED:
            self.current_track = self.jump_to_track
            self.jump_to_track = None
        else:
            # If shuffle
            if self.shuffle:
                self.process_shuffle()

            # If repeat is on SINGLE
            elif self.repeat == Repeat.SINGLE:
                await self.send_finished_message()
                await self.play()
                return

            # If last track and repeat is OFF
            elif self.is_last_track and self.repeat == Repeat.OFF:
                if self.autoplay:
                    try:
                        await self.send_finished_message()
                        await self.process_autoplay()
                    except ApiError:
                        return
                else:
                    await self.send_finished_message(detailed=True)
                    self.state = PlayerState.STOPPED
                    return

            # If last track and repeat is ALL
            elif self.is_last_track and self.repeat == Repeat.ALL:
                await self.send_finished_message()
                self.track_list.append(0)

            else:
                await self.send_finished_message()
                self.track_list.append(self.track_list[self.current_track] + 1)

            self.current_track += 1

        self.loop.create_task(self.play())

    def next(self):
        self.connection.stop()

    def jump(self, index):
        self.track_list.append(index)
        self.jump_to_track = self.current_track + 1
        self.state = PlayerState.JUMPED
        self.connection.stop()

    async def reset(self, timeout=None, clear_cache=True):
        self.state = PlayerState.NONE
        await self.disconnect(force=True, timeout=timeout)
        await self.clear_messages()
        if clear_cache:
            self.delete_cache()
        self.queue = []
        self.player_controls = None

    async def stop(self):
        await self.clear_messages()
        self.state = PlayerState.STOPPED
        self.next()

    async def remove_song(self, index: int):
        self.queue.pop(index)

        if len(self.track_list) > 0:
            for i, track in enumerate(self.track_list):
                if track > index:
                    self.track_list[i] -= 1

        # if current track is playing now
        if self.track_list[self.current_track] == index:
            self.current_track -= 1
            self.state = PlayerState.REMOVED
            self.next()

        if self.track_list[self.current_track] > index:
            self.current_track -= 1
            await self.refresh_player_message(embed=True)

    def process_shuffle(self) -> None:
        def choices():
            return [x for x in range(0, len(self.queue)) if x not in self.shuffled_list]

        if len(self.queue) == 1:
            self.shuffled_list = []
        elif len(self.shuffled_list) == 0 or len(choices()) == 0:
            self.shuffled_list = [self.track_list[self.current_track]]
            return self.process_shuffle()

        index = random.choice(choices())
        self.shuffled_list.append(index)
        self.track_list.append(index)

    async def process_autoplay(self) -> None:
        related_video_id = await YTMusic().get_related_video(
            self.now_playing, playlist=list(map(lambda track: track['id'], self.queue))
        )

        if not related_video_id:
            await self.ctx.channel.send(embed=Embed(t('music.no_related_video_found')))
            raise ApiError('No related video found.')

        ytdl_info = await Ytdl().extract_info('https://www.youtube.com/watch?v=' + related_video_id)
        data = ytdl_info.get_track()

        if data:
            self.add_to_queue(data, requested=bot.user)
            self.track_list.append(self.track_list[self.current_track] + 1)

    async def send_playing_message(self) -> None:
        if not self.now_playing:
            return

        log.cmd(
            self.ctx, t('music.now_playing.title', title=self.now_playing['title']), user=self.now_playing['requested']
        )

        await self.clear_messages()
        self.player_controls.initialize()

        self.messages['playing'] = await self.channel.send(
            embed=self.get_playing_embed(), view=self.player_controls.get(), silent=True
        )

    async def send_finished_message(self, detailed=False) -> None:
        log.cmd(
            self.ctx,
            t('music.finished_playing.title', title=self.last_track['title']),
            user=self.last_track['requested'],
        )

        await self.clear_messages()
        self.player_controls.initialize()

        message = await self.channel.send(
            embed=self.get_finished_embed() if detailed else self.get_simplified_finished_message(),
            view=self.player_controls.get() if detailed else None,
            silent=True,
        )

        # Will replace by simplified after
        if detailed:
            self.messages['finished'] = message

    async def clear_messages(self):
        if self.messages['finished']:
            await bot.delete_message(self.messages['finished'])
            await self.channel.send(embed=self.get_simplified_finished_message(), silent=True)

        await bot.delete_message(self.messages['playing'])
        self.messages['playing'] = None
        self.messages['finished'] = None

    async def refresh_player_message(self, *, embed=False):
        self.player_controls.refresh()

        if self.messages['playing']:
            await bot.edit_message(
                self.messages['playing'],
                embed=self.get_playing_embed() if embed else MISSING,
                view=self.player_controls.get(),
            )
        elif self.messages['finished']:
            await bot.edit_message(
                self.messages['finished'],
                embed=self.get_finished_embed() if embed else MISSING,
                view=self.player_controls.get(),
            )

    def get_footer(self, now_playing):
        return [
            str(now_playing['requested']),
            now_playing['formatted_duration'],
            t('music.shuffle_footer', shuffle='on' if self.shuffle else 'off'),
            t('music.repeat_footer', repeat=Repeat(self.repeat).name.lower()),
            t('music.autoplay_footer', autoplay='on' if self.autoplay else 'off'),
        ]

    def get_playing_embed(self):
        return self.get_track_embed(self.now_playing).set_author(
            name=t('music.now_playing.index', index=self.now_playing['index']),
            icon_url=ICONS['music'],
        )

    def get_finished_embed(self):
        return self.get_track_embed(self.last_track).set_author(
            name=t('music.finished_playing.index', index=self.last_track['index']),
            icon_url=ICONS['music'],
        )

    def get_track_embed(self, track):
        footer = self.get_footer(track)
        embed = Embed(title=track['title'], url=track['url'])
        embed.set_footer(text=' | '.join(footer), icon_url=track['requested'].display_avatar)

        return embed

    def get_simplified_finished_message(self):
        title = self.last_track['title']
        url = self.last_track['url']

        formatted_title = f'[{title}]({url})' if url else title

        return Embed(f'{t("music.finished_playing.index", index=self.last_track["index"])}: {formatted_title}')

    @staticmethod
    def has_cache(guild_id):
        file = PLAYER_CACHE_PATH % guild_id
        return path.exists(file)

    @staticmethod
    async def load_cache(guild_id):
        file = PLAYER_CACHE_PATH % guild_id

        try:
            with open(file, 'r') as f:

                def map_queue(track):
                    track['requested'] = bot.get_user(track['requested'])
                    return track

                cache = json.load(f)
                channel = bot.get_channel(cache['channel_id'])

                if not channel:
                    raise PlayerError("Can't find channel.")

                origin = await channel.send(embed=Embed('Picking up where you left off...'))

                player = await Player.get_instance(origin)
                player.queue = list(map(map_queue, cache['queue']))
                player.current_track = cache['current_track']
                player.track_list = cache['track_list']
                player.shuffled_list = cache['shuffled_list']
                player.state = PlayerState.get_by_value(cache['state'])
                player.last_voice_channel = bot.get_channel(cache['voice_channel_id'])

                if player.state == PlayerState.PLAYING:
                    await player.connect()
                    await player.play()

                await origin.delete()
        except Exception as error:
            log.error(error)
        finally:
            os.remove(file)

    def save_cache(self):
        if len(self.queue) == 0:
            return

        file = PLAYER_CACHE_PATH % self.ctx.guild.id

        with open(file, 'w') as f:

            def map_queue(track):
                if hasattr(track['requested'], 'id'):
                    track['requested'] = track['requested'].id
                track['stream'] = None
                return track

            # noinspection PyTypeChecker
            json.dump(
                {
                    'voice_channel_id': self.last_voice_channel.id,
                    'channel_id': self.ctx.channel.id,
                    'queue': list(map(map_queue, self.queue)),
                    'current_track': self.current_track,
                    'track_list': self.track_list,
                    'shuffled_list': self.shuffled_list,
                    'state': self.state.value,
                },
                f,
                indent=4,
            )

    def delete_cache(self):
        file = PLAYER_CACHE_PATH % self.ctx.guild.id

        if not self.has_cache(self.ctx.guild.id):
            return

        try:
            os.remove(file)
        except Exception as error:
            log.error(error)

    def add_to_queue(self, data: Union[List, dict], *, requested: discord.User = None) -> None:
        if not data:
            return

        if not isinstance(data, list):
            data = [data]

        for info in data:
            info['requested'] = requested
            self.queue.append(info)

        # Update next button
        if self.player_controls.next_disabled:
            self.loop.create_task(self.refresh_player_message())
