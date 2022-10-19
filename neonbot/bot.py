import asyncio
import re
import sys
from glob import glob
from os import sep
from time import time
from typing import Optional, Tuple, Union, Any

import discord
from aiohttp import ClientSession, ClientTimeout
from discord.ext import commands
from discord.utils import oauth_url
from envparse import env

from . import __version__
from .classes.database import Database
from .utils import log
from .utils.constants import PERMISSIONS


class NeonBot(commands.Bot):
    def __init__(self):
        self.default_prefix = env.str("DEFAULT_PREFIX", default=".")
        self.owner_ids = set(env.list("OWNER_IDS", default=[], subcast=int))
        self.user_agent = f"NeonBot v{__version__}"
        self.loop = asyncio.get_event_loop()
        super().__init__(intents=discord.Intents.all(), command_prefix=self.default_prefix)

        self.db = Database(self)
        self._settings = None
        self.app_info: Optional[discord.AppInfo] = None
        self.base_guild_id = env.int('BOT_GUILD_ID')
        self.session: Optional[ClientSession] = None

    @property
    def settings(self):
        return self._settings.get()

    async def initialize(self):
        self.db.initialize()
        self._settings = await self.db.get_settings()
        self.status, self.activity = self.get_presence()

    def get_presence(self) -> Tuple[discord.Status, discord.Activity]:
        activity_type = self.settings.get('activity_type').lower()
        activity_name = self.settings.get('activity_name')
        status = self.settings.get('status')

        return (
            discord.Status[status],
            discord.Activity(
                name=activity_name, type=discord.ActivityType[activity_type]
            ),
        )

    async def setup_hook(self):
        self.session = ClientSession(timeout=ClientTimeout(total=30))

        await self.add_cogs()

        # This copies the global commands over to your guild.
        async for guild in self.fetch_guilds():
            self.tree.copy_global_to(guild=discord.Object(guild.id))
            await self.tree.sync(guild=discord.Object(guild.id))
            log.info(f"Command synced to: {guild}")

    async def add_cogs(self):
        files = sorted(glob(f"neonbot{sep}cogs{sep}[!_]*.py"))
        extensions = list(map(lambda x: re.split(r"[{0}.]".format(re.escape(sep)), x)[-2], files))
        start_time = time()

        print(file=sys.stderr)

        for extension in extensions:
            log.info(f"Loading {extension} cog...")
            await self.load_extension("neonbot.cogs." + extension)

        print(file=sys.stderr)

        log.info(f"Loaded {len(extensions)} cogs after {(time() - start_time):.2f}s")

    async def fetch_app_info(self) -> None:
        if not self.app_info:
            self.app_info = await self.application_info()

    async def send_invite_link(self, message: discord.Message) -> None:
        url = oauth_url(
            self.app_info.id,
            permissions=discord.Permissions(permissions=PERMISSIONS),
            scopes=('bot', 'applications.commands')
        )
        await message.channel.send(f"Bot invite link: {url}")
        log.info(f"Sent an invite link to: {message.author}")

    async def send_response(self, interaction: discord.Interaction, *args, **kwargs):
        if not interaction.response.is_done():
            await interaction.response.send_message(*args, **kwargs)
        elif interaction.response.type in (discord.InteractionResponseType.deferred_message_update,
                                           discord.InteractionResponseType.deferred_channel_message):
            await interaction.followup.send(*args, **kwargs)
        else:
            await interaction.edit_original_response(*args, view=None, **kwargs)

    async def edit_message(self, message: Union[discord.Message, None], **kwargs) -> None:
        if message is None:
            return

        try:
            await message.edit(**kwargs)
        except discord.NotFound:
            pass

    async def delete_message(self, *messages: Union[discord.Message, None]) -> None:
        await asyncio.gather(
            *[message.delete() for message in messages if message is not None],
            return_exceptions=True
        )

    async def send_to_owner(self, *args: Any, **kwargs: Any) -> None:
        await self.get_user(self.app_info.owner.id).send(*args, **kwargs)

    async def start(self, *args, **kwargs) -> None:
        await self.initialize()
        await super().start(*args, **kwargs)

    def run(self, *args, **kwargs):
        super().run(env.str('TOKEN'), *args, **kwargs)

    def _handle_ready(self) -> None:
        pass

    def set_ready(self):
        self._ready.set()
