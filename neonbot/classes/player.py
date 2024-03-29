from __future__ import annotations

import asyncio
import random
from typing import Union, List, Optional, Dict

import discord
from discord.ext import commands
from discord.utils import MISSING
from i18n import t

from neonbot.classes.embed import Embed
from neonbot.classes.player_controls import PlayerControls
from neonbot.classes.ytdl import ytdl
from neonbot.enums import Repeat
from neonbot.enums.player_state import PlayerState
from neonbot.models.guild import Guild
from neonbot.utils import log
from neonbot.utils.constants import FFMPEG_OPTIONS, ICONS
from neonbot.utils.functions import delete_message


class Player:
    servers = {}

    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self.channel = ctx.channel
        self.loop = asyncio.get_event_loop()
        self.settings = Guild.get_instance(ctx.guild.id)
        self.player_controls = PlayerControls(self)
        self.queue = []
        self.connection = None
        self.current_queue = 0
        self.track_list = [0]
        self.shuffled_list = []
        self.messages: Dict[str, Optional[discord.Message]] = dict(
            playing=None,
            finished=None,
            paused=None,
            resumed=None,
            auto_paused=None,
            repeat=None,
            shuffle=None
        )
        self.last_track = None
        self.state = PlayerState.STOPPED

    @staticmethod
    def get_instance(ctx: commands.Context) -> Player:
        guild_id = ctx.guild.id

        if guild_id not in Player.servers.keys():
            Player.servers[guild_id] = Player(ctx)

        return Player.servers[guild_id]

    @property
    def volume(self) -> int:
        return self.settings.get('music.volume')

    @property
    def repeat(self) -> Repeat:
        return self.settings.get('music.repeat')

    @property
    def is_shuffle(self) -> bool:
        return self.settings.get('music.shuffle')

    @property
    def is_last_track(self):
        return self.track_list[self.current_queue] == len(self.queue) - 1

    @property
    def now_playing(self) -> Union[dict, None]:
        try:
            return {
                'index': self.track_list[self.current_queue] + 1,
                **self.queue[self.track_list[self.current_queue]]
            }
        except IndexError:
            return None

    @now_playing.setter
    def now_playing(self, value) -> None:
        try:
            self.queue[self.track_list[self.current_queue]] = value
        except IndexError:
            pass

    async def connect(self):
        if self.ctx.guild.voice_client:
            return

        self.connection = await self.ctx.author.voice.channel.connect()
        log.cmd(self.ctx, t('music.player_connected', channel=self.ctx.author.voice.channel))

    async def set_repeat(self, mode: Repeat):
        await delete_message(self.messages['repeat'])
        await self.settings.update({'music.repeat': mode.value})
        self.messages['repeat'] = await self.channel.send(
            embed=Embed(t('music.repeat_changed', mode=mode.name.lower())),
            delete_after=5
        )
        await self.refresh_player_message(embed=True)

    async def set_shuffle(self):
        await delete_message(self.messages['shuffle'])
        await self.settings.update({'music.shuffle': not self.is_shuffle})
        self.messages['shuffle'] = await self.channel.send(
            embed=Embed(t('music.shuffle_changed', mode='on' if self.is_shuffle else 'off')),
            delete_after=5
        )
        await self.refresh_player_message(embed=True)

    async def set_volume(self, volume: int):
        if self.connection and self.connection.source:
            self.connection.source.volume = volume / 100

        await self.settings.update({'music.volume': not self.volume})
        await self.refresh_player_message(embed=True)

    async def pause(self):
        if self.connection.is_paused():
            return

        self.connection.pause()
        log.cmd(self.ctx, t('music.player_paused'))

        await delete_message(self.messages['paused'], self.messages['resumed'])
        self.messages['paused'] = await self.ctx.send(embed=Embed(t('music.player_paused')))
        await self.refresh_player_message()

    async def play(self) -> None:
        if not self.connection or not self.connection.is_connected() or self.connection.is_playing():
            return

        try:
            if not self.now_playing.get('stream'):
                info = await ytdl.process_entry(self.now_playing)
                info = ytdl.parse_info(info)
                self.now_playing = {**self.now_playing, **info}

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
            else:
                msg = t('music.player_error')

            log.exception(msg, error)
            await self.channel.send(embed=Embed(msg))

    async def after(self, error=None):
        if error:
            log.error(error)
            return

        self.last_track = self.now_playing

        if self.state == PlayerState.STOPPED:
            return

        # If shuffle
        if self.is_shuffle:
            self.process_shuffle()

        # If repeat is on SINGLE
        elif self.repeat == Repeat.SINGLE:
            await self.play()
            return

        # If last track and repeat is OFF
        elif self.is_last_track and self.repeat == Repeat.OFF.value:
            await self.send_finished_message()
            return

        # If last track and repeat is ALL
        elif self.is_last_track and self.repeat == Repeat.ALL.value:
            self.track_list.append(0)

        else:
            self.track_list.append(self.track_list[self.current_queue] + 1)

        self.current_queue += 1
        await self.send_finished_message()
        await self.play()

    def next(self):
        if self.connection.is_playing():
            self.connection.stop()

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

        await self.clear_playing_messages()
        self.player_controls.initialize()

        self.messages['playing'] = await self.channel.send(
            embed=self.get_playing_embed(), view=self.player_controls.get()
        )

    async def send_finished_message(self) -> None:
        log.cmd(
            self.ctx,
            t('music.finished_playing.title', title=self.last_track['title']),
            user=self.last_track['requested'],
        )

        await self.clear_playing_messages()
        self.player_controls.initialize()

        self.messages['finished'] = await self.channel.send(
            embed=self.get_finished_embed(),
            view=self.player_controls.get()
        )

    async def clear_playing_messages(self):
        await delete_message(
            self.messages['playing'],
            self.messages['finished'],
            self.messages['paused'],
            self.messages['resumed']
        )
        self.messages['playing'] = None
        self.messages['finished'] = None

    async def refresh_player_message(self, *, embed=False, refresh=True):
        self.player_controls.refresh()

        if not refresh:
            return

        if self.messages['playing']:
            await self.messages['playing'].edit(
                embed=self.get_playing_embed() if embed else MISSING,
                view=self.player_controls.get()
            )
        elif self.messages['finished']:
            await self.messages['finished'].edit(
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
            name=t('music.now_playing.index', index=self.last_track['index']),
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

    def add_to_queue(self, data: Union[List, dict], *, requested: discord.User = None) -> None:
        if not data:
            return

        if not isinstance(data, list):
            data = [data]

        for info in data:
            info['requested'] = requested
            self.queue.append(info)
