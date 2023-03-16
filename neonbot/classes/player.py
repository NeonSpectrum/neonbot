from __future__ import annotations

import asyncio
import random
from typing import Union, List, Optional, Dict

import discord
from discord.ext import commands, tasks
from discord.utils import MISSING
from i18n import t

from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.classes.player_controls import PlayerControls
from neonbot.classes.ytdl import Ytdl
from neonbot.enums import Repeat, PlayerState
from neonbot.models.server import Server
from neonbot.utils import log
from neonbot.utils.constants import FFMPEG_OPTIONS, ICONS
from neonbot.utils.exceptions import YtdlError


class Player:
    servers: dict[int, Player] = {}

    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self.loop = asyncio.get_event_loop()
        self.settings = Server.get_instance(ctx.guild.id)
        self.player_controls = PlayerControls(self)
        self.queue = []
        self.current_queue = 0
        self.track_list = [0]
        self.shuffled_list = []
        self.messages: Dict[str, Optional[discord.Message]] = dict(
            playing=None,
            finished=None,
        )
        self.last_track = None
        self.last_voice_channel: Optional[discord.VoiceChannel] = None
        self.state = PlayerState.STOPPED

    @property
    def channel(self):
        return self.ctx.channel

    @property
    def connection(self) -> Optional[discord.VoiceClient]:
        return self.ctx.voice_client

    @staticmethod
    async def get_instance(interaction: discord.Interaction) -> Player:
        ctx = await bot.get_context(interaction)
        guild_id = ctx.guild.id

        if guild_id not in Player.servers.keys():
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
    def volume(self) -> int:
        return self.settings.music.volume

    @property
    def repeat(self) -> int:
        return self.settings.music.repeat

    @property
    def is_shuffle(self) -> bool:
        return self.settings.music.shuffle

    @property
    def is_last_track(self):
        return self.track_list[self.current_queue] == len(self.queue) - 1

    @property
    def now_playing(self) -> Union[dict, None]:
        try:
            return {
                **self.queue[self.track_list[self.current_queue]],
                'index': self.track_list[self.current_queue] + 1
            }
        except IndexError:
            return None

    @now_playing.setter
    def now_playing(self, value) -> None:
        try:
            self.queue[self.track_list[self.current_queue]] = value
        except IndexError:
            pass

    def get_track(self, index: int) -> dict:
        return self.queue[index]

    @tasks.loop(count=1)
    async def pause_timeout(self) -> None:
        await asyncio.sleep(5)

        await self.pause(requester=bot.user)

    @tasks.loop(count=1)
    async def reset_timeout(self) -> None:
        await asyncio.sleep(60)

        await self.reset()
        self.remove_instance()

    async def connect(self, channel: discord.VoiceChannel):
        if self.connection:
            return

        if not channel and self.last_voice_channel:
            await self.last_voice_channel.connect()
        else:
            self.last_voice_channel = await channel.connect()

        log.cmd(self.ctx, t('music.player_connected', channel=channel))

    async def disconnect(self, force=True) -> None:
        if self.connection and self.connection.is_connected():
            await self.connection.disconnect(force=force)

    async def set_repeat(self, mode: Repeat, requester: discord.User):
        self.settings.music.repeat = mode.value
        await self.settings.save_changes()

        await self.channel.send(
            embed=Embed(t('music.repeat_changed', mode=mode.name.lower(), user=requester.mention))
        )
        await self.refresh_player_message(embed=True)

    async def set_shuffle(self, requester: discord.User):
        self.settings.music.shuffle = not self.is_shuffle
        await self.settings.save_changes()

        await self.channel.send(
            embed=Embed(t('music.shuffle_changed', mode='on' if self.is_shuffle else 'off', user=requester.mention))
        )
        await self.refresh_player_message(embed=True)

    async def set_volume(self, volume: int):
        if self.connection and self.connection.source:
            self.connection.source.volume = volume / 100

        self.settings.music.volume = volume
        await self.settings.save_changes()

        await self.refresh_player_message(embed=True)

    async def pause(self, requester: discord.User, auto=False):
        if self.connection.is_paused() or not self.connection.is_playing():
            return

        self.connection.pause()
        log.cmd(self.ctx, t('music.player_paused'))

        self.state = PlayerState.AUTO_PAUSED if auto else PlayerState.PAUSED

        await self.channel.send(embed=Embed(t('music.player_paused', user=requester.mention)))
        await self.refresh_player_message()

    async def resume(self, requester: discord.User):
        if not self.connection.is_paused():
            return

        self.connection.resume()
        log.cmd(self.ctx, t('music.player_resumed'))

        self.state = PlayerState.PLAYING

        await self.channel.send(embed=Embed(t('music.player_resumed', user=requester.mention)))
        await self.refresh_player_message()

    async def play(self) -> None:
        if not self.connection or not self.connection.is_connected() or self.connection.is_playing():
            return

        self.pre_play()

        try:
            if not self.now_playing.get('stream'):
                ytdl_info = await Ytdl().process_entry(self.now_playing)
                info = ytdl_info.get_track(detailed=True)
                self.now_playing = {'index': self.track_list[self.current_queue] + 1, **self.now_playing, **info}

            song = discord.FFmpegPCMAudio(
                self.now_playing['stream'],
                before_options=None if not self.now_playing['is_live'] else FFMPEG_OPTIONS,
            )
            source = discord.PCMVolumeTransformer(song, volume=self.volume / 100)
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
            await self.channel.send(embed=Embed(msg))

    def pre_play(self):
        # Play recently added song if added while player is finished playing
        if (
            self.repeat == Repeat.OFF
            and not self.connection.is_playing()
            and not self.connection.is_paused()
            and self.track_list[self.current_queue] == len(self.queue) - 2
        ):
            self.track_list.append(self.track_list[self.current_queue] + 1)
            self.current_queue += 1

    async def after(self, error=None):
        if error:
            log.error(error)
            return

        self.last_track = self.now_playing

        if self.state == PlayerState.STOPPED:
            return

        if self.state != PlayerState.JUMPED:
            # If shuffle
            if self.is_shuffle:
                self.process_shuffle()

            # If repeat is on SINGLE
            elif self.repeat == Repeat.SINGLE:
                await self.play()
                return

            # If last track and repeat is OFF
            elif self.is_last_track and self.repeat == Repeat.OFF:
                await self.send_finished_message(detailed=True)
                return

            # If last track and repeat is ALL
            elif self.is_last_track and self.repeat == Repeat.ALL:
                self.track_list.append(0)

            else:
                self.track_list.append(self.track_list[self.current_queue] + 1)

        self.current_queue += 1

        if self.state != PlayerState.REMOVED:
            await self.send_finished_message()

        await self.play()

    def next(self):
        self.connection.stop()

    def jump(self, index):
        self.track_list.append(index - 1)
        self.state = PlayerState.JUMPED
        self.connection.stop()

    async def reset(self):
        self.state = PlayerState.STOPPED
        await self.disconnect(force=True)
        await self.clear_messages()

    async def remove_song(self, index: int):
        self.queue.pop(index)

        if len(self.track_list) > 0:
            for i, track in enumerate(self.track_list):
                if track > index:
                    self.track_list[i] -= 1

        # if current track is playing now
        if self.track_list[self.current_queue] == index:
            self.current_queue -= 1
            self.state = PlayerState.REMOVED
            self.next()

        if self.track_list[self.current_queue] > index:
            self.current_queue -= 1
            await self.refresh_player_message(embed=True)

    def process_shuffle(self) -> bool:
        def choices():
            return [x for x in range(0, len(self.queue)) if x not in self.shuffled_list]

        if len(self.queue) == 1:
            self.shuffled_list = []
        elif len(self.shuffled_list) == 0 or len(choices()) == 0:
            self.shuffled_list = [self.track_list[self.current_queue]]
            return self.process_shuffle()

        index = random.choice(choices())
        self.shuffled_list.append(index)
        self.track_list.append(index)

    async def send_playing_message(self) -> None:
        if not self.now_playing:
            return

        log.cmd(self.ctx, t('music.now_playing.title', title=self.now_playing['title']),
                user=self.now_playing['requested'])

        await self.clear_messages()
        self.player_controls.initialize()

        self.messages['playing'] = await self.channel.send(
            embed=self.get_playing_embed(), view=self.player_controls.get()
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
            view=self.player_controls.get() if detailed else None
        )

        # Will replace by simplified after
        if detailed:
            self.messages['finished'] = message

    async def clear_messages(self):
        if self.messages['finished']:
            await bot.delete_message(self.messages['finished'])
            await self.channel.send(embed=self.get_simplified_finished_message())

        await bot.delete_message(self.messages['playing'])
        self.messages['playing'] = None
        self.messages['finished'] = None

    async def refresh_player_message(self, *, embed=False, refresh=True):
        self.player_controls.refresh()

        if not refresh:
            return

        if self.messages['playing']:
            await bot.edit_message(
                self.messages['playing'],
                embed=self.get_playing_embed() if embed else MISSING,
                view=self.player_controls.get()
            )
        elif self.messages['finished']:
            await bot.edit_message(
                self.messages['finished'],
                embed=self.get_finished_embed() if embed else MISSING,
                view=self.player_controls.get()
            )

    def get_footer(self, now_playing):
        return [
            str(now_playing['requested']),
            now_playing['formatted_duration'],
            t('music.volume_footer', volume=self.volume),
            t('music.shuffle_footer', shuffle='on' if self.is_shuffle else 'off'),
            t('music.repeat_footer', repeat=Repeat(self.repeat).name.lower()),
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
        footer = [
            str(track['requested']),
            track['formatted_duration'],
            t('music.volume_footer', volume=self.volume),
            t('music.shuffle_footer', shuffle='on' if self.is_shuffle else 'off'),
            t('music.repeat_footer', repeat=Repeat(self.repeat).name.lower()),
        ]

        embed = Embed(title=track['title'], url=track['url'])
        embed.set_footer(
            text=' | '.join(footer), icon_url=track['requested'].display_avatar
        )

        return embed

    def get_simplified_finished_message(self):
        title = self.last_track['title']
        url = self.last_track['url']

        return Embed(f"{t('music.finished_playing.index', index=self.last_track['index'])}: [{title}]({url})")

    def add_to_queue(self, data: Union[List, dict], *, requested: discord.User = None) -> None:
        if not data:
            return

        if not isinstance(data, list):
            data = [data]

        for info in data:
            info['requested'] = requested
            self.queue.append(info)
