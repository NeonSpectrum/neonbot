import asyncio
from typing import List, Optional
from typing import TYPE_CHECKING

from discord.ext import commands
from discord.utils import MISSING
from i18n import t
from lavalink import AudioTrack

from neonbot.classes.discord.embed import Embed
from neonbot.classes.player.player_controls import PlayerControls
from neonbot.dataclasses import PlayerMessage
from neonbot.enums import MessageType, Repeat
from neonbot.utils import log
from neonbot.utils.constants import ICONS
from neonbot.utils.functions import format_milliseconds

if TYPE_CHECKING:
    from neonbot import NeonBot


class PlayerMessageManager:
    def __init__(self, bot: 'NeonBot', guild_id: int):
        self.bot = bot
        self.guild_id = guild_id
        self.data: List[PlayerMessage] = []
        self.player_controls = PlayerControls(self.bot, guild_id)
        self.ctx: Optional[commands.Context['NeonBot']] = None

    @property
    def player(self):
        return self.bot.lavalink.player_manager.get(self.guild_id)

    def set_ctx(self, ctx: commands.Context['NeonBot']):
        self.ctx = ctx

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
        return [
            self.bot.get_user(track.requester).display_name,
            format_milliseconds(track.duration),
            t('music.shuffle_footer', shuffle='on' if self.player.shuffle else 'off'),
            t('music.repeat_footer', repeat=Repeat(self.player.loop).name.lower()),
            t('music.autoplay_footer', autoplay='on' if self.player.autoplay else 'off'),
        ]

    def get_track_embed(self, track: AudioTrack):
        footer = self.get_footer(track)
        embed = Embed(title=track.title, url=track.uri)
        embed.set_footer(text=' | '.join(footer), icon_url=str(self.bot.get_user(track.requester).display_avatar))

        return embed

    def get_playing_embed(self, track: AudioTrack):
        return self.get_track_embed(track).set_author(
            name=t('music.now_playing.index', index=track.extra.get('index') + 1),
            icon_url=ICONS.get(track.source_name, ICONS.get('music')),
        )

    def get_finished_embed(self, track: AudioTrack, compact=True):
        if compact:
            formatted_title = f'[{track.title}]({track.uri})' if track.uri else track.title
            return Embed(f'{t("music.finished_playing.index", index=track.extra.get('index') + 1)}: {formatted_title}')

        return self.get_track_embed(track).set_author(
            name=t('music.finished_playing.index', index=track.extra.get('index') + 1),
            icon_url=ICONS.get(track.source_name, ICONS.get('music')),
        )

    def get_compact_finished_embed(self, track: AudioTrack):
        formatted_title = f'[{track.title}]({track.uri})' if track.uri else track.title

        return Embed(f'{t("music.finished_playing.index", index=track.extra.get('index') + 1)}: {formatted_title}')

    async def replace_to_finished_playing(self, player_message: PlayerMessage):
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
            view=self.player_controls.get()
        )
        player_message.compact = False

    async def edit_message(self, player_message: PlayerMessage, *args, **kwargs):
        player_message.message = await self.bot.edit_message(player_message.message, *args, **kwargs)

    async def send_message(self, data: PlayerMessage):
        if self.ctx is None:
            log.warn('self.ctx not yet available.')
            return

        self.player_controls.initialize()

        data.message = await self.ctx.channel.send(embed=self.get_playing_embed(data.track), view=self.player_controls.get())
        self.add(data)

    def refresh_player_controls(self, *, embed=False):
        for player_message in self.data:
            if len(player_message.message.components) == 0:
                continue

            if player_message.type == MessageType.PLAYING:
                self.bot.loop.create_task(self.edit_message(
                    player_message,
                    embed=self.get_playing_embed(player_message.track) if embed else MISSING,
                    view=self.player_controls.get(),
                ))
            elif player_message.type == MessageType.FINISHED:
                self.bot.loop.create_task(self.edit_message(
                    player_message,
                    embed=self.get_finished_embed(player_message.track) if embed else MISSING,
                    view=self.player_controls.get(),
                ))
