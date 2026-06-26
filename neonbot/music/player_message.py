import asyncio
from typing import List, Optional, TYPE_CHECKING

import discord
from discord.utils import MISSING
from i18n import t
from lavalink import AudioTrack

from neonbot.discord_ui.embed import Embed
from neonbot.music.enums import PlayerMessage, MessageType, Repeat
from neonbot.music.player_controls import PlayerControls
from neonbot.utils import log
from neonbot.utils.constants import ICONS
from neonbot.utils.functions import format_milliseconds

if TYPE_CHECKING:
    from neonbot import NeonBot
    from neonbot.music.player import Player


class PlayerMessageManager:
    def __init__(self, bot: 'NeonBot', guild_id: int):
        self.bot = bot
        self.guild_id = guild_id
        self.data: List[PlayerMessage] = []
        self.player_controls = PlayerControls(self.bot, guild_id)
        self.channel: Optional[discord.TextChannel] = None

    @property
    def player(self) -> 'Player':
        return self.bot.get_player_instance(self.guild_id)

    def set_channel(self, channel: discord.TextChannel):
        self.channel = channel

    def add(self, data: PlayerMessage):
        self.data.append(data)

    def clear(self):
        self.data = []

    def get_latest_message(self, message_type: MessageType):
        for player_message in self.data[::-1]:
            if player_message.type == message_type:
                return player_message

        return None

    def get_footer(self, track):
        user = self.bot.get_user(track.requester)
        requester_name = user.display_name if user else t('music.unknown_requester')
        return [
            requester_name,
            format_milliseconds(track.duration),
            t('music.shuffle_footer', shuffle='on' if self.player.shuffle else 'off'),
            t('music.repeat_footer', repeat=Repeat(self.player.loop).name.lower()),
            t('music.autoplay_footer', autoplay='on' if self.player.autoplay else 'off'),
        ]

    def get_track_embed(self, track: AudioTrack):
        footer = self.get_footer(track)
        embed = Embed(title=track.title, url=track.uri)
        user = self.bot.get_user(track.requester)
        icon_url = user.display_avatar.url if user else None
        embed.set_footer(text=' | '.join(footer), icon_url=icon_url)

        return embed

    def get_playing_embed(self, track: AudioTrack):
        index = self.player.track_list.index(track) + 1 if track in self.player.track_list else '?'
        return self.get_track_embed(track).set_author(
            name=t('music.now_playing.index', index=index),
            icon_url=ICONS.get(track.source_name, ICONS.get('music')),
        )

    def get_finished_embed(self, track: AudioTrack, compact=True):
        index = self.player.track_list.index(track) + 1 if track in self.player.track_list else '?'
        if compact:
            formatted_title = f'[{track.title}]({track.uri})' if track.uri else track.title
            return Embed(f'{t("music.finished_playing.index", index=index)}: {formatted_title}')

        return self.get_track_embed(track).set_author(
            name=t('music.finished_playing.index', index=index),
            icon_url=ICONS.get(track.source_name, ICONS.get('music')),
        )

    async def replace_to_finished_playing(self, player_message: Optional[PlayerMessage]):
        if player_message is None:
            return
        await self.edit_message(
            player_message,
            embed=self.get_finished_embed(player_message.track, compact=True),
            view=None
        )
        player_message.compact = True

    async def replace_all_to_compact(self):
        futures = []

        for player_message in self.data:
            if not player_message.compact:
                futures.append(self.edit_message(
                    player_message,
                    embed=self.get_finished_embed(player_message.track, compact=True),
                    view=None
                ))

        await asyncio.gather(*futures)

    async def replace_to_non_compact(self, player_message: PlayerMessage):
        await self.edit_message(
            player_message,
            embed=self.get_finished_embed(player_message.track, compact=False),
            view=self.player_controls.get(),
        )
        player_message.compact = False

    async def edit_message(self, player_message: PlayerMessage, *args, **kwargs):
        player_message.message = await self.bot.edit_message(player_message.message, *args, **kwargs)

    async def send_message(self, data: PlayerMessage):
        if not self.channel:
            log.warn('self.channel not yet available.')
            return

        self.player_controls.initialize()

        data.message = await self.channel.send(embed=self.get_playing_embed(data.track), view=self.player_controls.get(), silent=True)
        self.add(data)

    def refresh_player_controls(self, *, embed=False):
        tasks = []
        for player_message in self.data:
            if not player_message.message or len(player_message.message.components) == 0:
                continue

            if player_message.type == MessageType.PLAYING:
                tasks.append(self.edit_message(
                    player_message,
                    embed=self.get_playing_embed(player_message.track) if embed else MISSING,
                    view=self.player_controls.get(),
                ))
            elif player_message.type == MessageType.FINISHED:
                tasks.append(self.edit_message(
                    player_message,
                    embed=self.get_finished_embed(player_message.track) if embed else MISSING,
                    view=self.player_controls.get(),
                ))
        if tasks:
            self.bot.loop.create_task(asyncio.gather(*tasks, return_exceptions=True))
