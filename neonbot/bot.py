import asyncio
import os
import re
import signal
import sys
from concurrent.futures import Executor
from glob import glob
from os import sep
from time import time
from typing import Any, Optional, Union, TYPE_CHECKING

import aiohttp.client_exceptions
import discord
import psutil
from aiohttp import ClientSession, ClientTimeout
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import STATE_RUNNING
from discord import Activity, Status, Message
from discord.ext import commands
from discord.utils import oauth_url

from neonbot import __version__
from neonbot.classes.database import Database
from neonbot.classes.lavalink.client import Client
from neonbot.env import (
    DEFAULT_PREFIX,
    LAVALINK_HOST,
    LAVALINK_PASSWORD,
    LAVALINK_PORT,
    OWNER_GUILD_IDS,
    OWNER_IDS,
    SYNC_COMMANDS, DISABLED_COGS,
)
from neonbot.models.flyff import FlyffModel
from neonbot.models.guild import GuildModel
from neonbot.models.setting import SettingModel
from neonbot.utils import log
from neonbot.utils.constants import PERMISSIONS
from neonbot.utils.context_menu import load_context_menu
from neonbot.views.ExchangeGiftView import ExchangeGiftView

if TYPE_CHECKING:
    from neonbot.classes.player.player import Player


class NeonBot(commands.Bot):
    def __init__(self, executor: Executor):
        self.default_prefix = DEFAULT_PREFIX
        self.user_agent = f'NeonBot v{__version__}'
        self.loop = asyncio.get_event_loop()
        self.loop.set_default_executor(executor)
        super().__init__(
            intents=discord.Intents.all(),
            command_prefix=self.default_prefix,
            owner_ids=set(OWNER_IDS),
        )

        self.db = Database(self)
        self.app_info: Optional[discord.AppInfo] = None
        self.owner_guilds = OWNER_GUILD_IDS
        self.session: Optional[ClientSession] = None
        self.setting: Optional[SettingModel] = None
        self.flyff_settings: Optional[FlyffModel] = None
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_player_cache_loaded = False

        self.lavalink: Optional[Client] = None

    def get_presence(self) -> tuple[Status, Activity]:
        activity_type = self.setting.activity_type
        activity_name = self.setting.activity_name
        status = self.setting.status

        return (
            discord.Status[status],
            discord.Activity(name=activity_name, type=discord.ActivityType[activity_type]),
        )

    async def setup_hook(self):
        if not sys.platform.startswith('win'):
            self.loop.add_signal_handler(signal.SIGTERM,
                                         lambda: asyncio.create_task(self.close()))  # type: ignore[arg-type]

        await self.db.initialize()
        self.setting = await SettingModel.get_instance()
        self.flyff_settings = await FlyffModel.get_instance()
        self.status, self.activity = self.get_presence()
        self.session = ClientSession(timeout=ClientTimeout(total=30))
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()

        self.initialize_lavalink()

        await self.add_cogs()
        load_context_menu(self)

        guilds = [guild async for guild in self.fetch_guilds()]

        if SYNC_COMMANDS:
            await self.sync_command()

            # This copies the global commands over to your guild.
            await asyncio.gather(*[self.sync_command(guild) for guild in guilds])

        await self.db.start_migration(guilds)
        await self.db.get_guilds(guilds)

    async def sync_command(self, guild: Optional[discord.Guild] = None):
        await self.tree.sync(guild=guild)
        log.info(f'Command synced to: {guild or "Global"}')

    def start_listeners(self):
        from neonbot.classes.flyff import Flyff
        from neonbot.classes.panel import Panel

        Flyff.start_listener(self)

        for guild in self.guilds:
            server = GuildModel.get_instance(guild.id)

            if server and not server.exchange_gift.finish and server.exchange_gift.message_id:
                self.add_view(ExchangeGiftView(), message_id=server.exchange_gift.message_id)

            Panel.start_listener(self, guild.id)

    async def join_autojoin_voice_channels(self):
        for guild in self.guilds:
            server = GuildModel.get_instance(guild.id)

            if server.music.autojoin_channel_id is None:
                continue

            player = await self.create_player_instance(guild.id)

            vc: discord.VoiceChannel = self.get_channel(server.music.autojoin_channel_id)
            self.loop.create_task(player.connect(vc))

    async def create_player_instance(self, guild_id: int, *, ctx: Optional[commands.Context['NeonBot']] = None) -> 'Player':
        player: 'Player' = self.lavalink.player_manager.create(guild_id)

        if ctx:
            player.set_ctx(ctx)

        if not player.ctx:
            await player.set_default_ctx()

        return player

    def get_player_instance(self, guild_id: int) -> 'Player':
        return self.lavalink.player_manager.get(guild_id)

    def initialize_lavalink(self):
        self.lavalink = Client(self, self.user.id)
        self.lavalink.add_node(
            LAVALINK_HOST,
            LAVALINK_PORT,
            LAVALINK_PASSWORD,
            'asia'
        )

    async def add_cogs(self):
        files = sorted(glob(f'neonbot{sep}cogs{sep}[!_]*.py'))
        extensions = [re.split(r'[{0}.]'.format(re.escape(sep)), file)[-2] for file in files]
        start_time = time()
        process = psutil.Process(os.getpid())

        print(file=sys.stderr)

        futures = []

        for extension in extensions:
            if extension in DISABLED_COGS:
                continue

            log.info(f'Loading {extension} cog... [{(process.memory_info().rss / 1024000):.2f} MB]')
            futures.append(self.load_extension('neonbot.cogs.' + extension))

        await asyncio.gather(*futures)

        print(file=sys.stderr)

        log.info(f'Loaded {len(extensions)} cogs after {(time() - start_time):.2f}s\n')

    async def fetch_app_info(self) -> None:
        if not self.app_info:
            self.app_info = await self.application_info()

    async def send_invite_link(self, message: discord.Message) -> None:
        url = oauth_url(
            self.app_info.id,
            permissions=discord.Permissions(permissions=PERMISSIONS),
            scopes=('bot', 'applications.commands'),
        )
        await message.channel.send(f'Bot invite link: {url}')
        log.info(f'Sent an invite link to: {message.author}')

    async def update_presence(self):
        setting = await SettingModel.get_instance()

        await self.change_presence(
            activity=discord.Activity(name=setting.activity_name, type=discord.ActivityType[setting.activity_type]),
            status=getattr(discord.Status, setting.status),
        )

    async def send_response(self, interaction: discord.Interaction['NeonBot'], *args, **kwargs):
        if not interaction.response.is_done():
            await interaction.response.send_message(*args, **kwargs)
        elif (
            interaction.response.type
            == discord.InteractionResponseType.deferred_message_update
        ):
            await interaction.followup.send(*args, **kwargs)
        else:
            if 'view' not in kwargs:
                kwargs['view'] = None
            try:
                del kwargs['ephemeral']
            except KeyError:
                pass
            await interaction.edit_original_response(*args, **kwargs)

    async def edit_message(self, message: Union[discord.Message, None], *args, **kwargs) -> Message | None:
        if message is None:
            return None

        try:
            return await message.edit(*args, **kwargs)
        except (discord.DiscordException, aiohttp.client_exceptions.ClientError):
            pass

    async def delete_message(self, *messages: Union[discord.Message, None]) -> None:
        await asyncio.gather(*[message.delete() for message in messages if message is not None], return_exceptions=True)

    async def send_to_owner(self, *args: Any, **kwargs: Any) -> None:
        await self.get_user(self.app_info.owner.id).send(*args, **kwargs)

    async def close(self) -> None:
        if self.scheduler:
            log.info('Stopping scheduler...')
            if self.scheduler.state == STATE_RUNNING:
                self.scheduler.shutdown(wait=False)

        log.info('Saving all music...')

        log.info('Stopping all music...')
        await asyncio.gather(
            *[player.reset(timeout=3) for player in self.lavalink.player_manager.values()]
        )
        await self.lavalink.close()

        log.info('Closing session...')
        await self.session.close()

        log.info('Stopping bot...')
        await super().close()

    def _handle_ready(self) -> None:
        pass

    def set_ready(self):
        self._ready.set()
