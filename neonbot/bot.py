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
from .models.setting import Setting
from .utils import log
from .utils.constants import PERMISSIONS
from .utils.context_menu import load_context_menu


class NeonBot(commands.Bot):
    def __init__(self):
        self.default_prefix = env.str("DEFAULT_PREFIX", default=".")
        self.owner_ids = set(env.list("OWNER_IDS", default=[], subcast=int))
        self.user_agent = f"NeonBot v{__version__}"
        self.loop = asyncio.get_event_loop()
        super().__init__(intents=discord.Intents.all(), command_prefix=self.default_prefix)

        self.db = Database(self)
        self.app_info: Optional[discord.AppInfo] = None
        self.owner_guilds = env.list('OWNER_GUILD_IDS', default=[], subcast=int)
        self.session: Optional[ClientSession] = None
        self.setting: Optional[Setting] = None

    def get_presence(self) -> Tuple[discord.Status, discord.Activity]:
        activity_type = self.setting.activity_type
        activity_name = self.setting.activity_name
        status = self.setting.status

        return (
            discord.Status[status],
            discord.Activity(
                name=activity_name, type=discord.ActivityType[activity_type]
            ),
        )

    async def setup_hook(self):
        await self.db.initialize()
        self.setting = await Setting.get_instance()
        self.status, self.activity = self.get_presence()
        self.session = ClientSession(timeout=ClientTimeout(total=30))

        await self.add_cogs()
        load_context_menu(self)

        guilds = [guild async for guild in self.fetch_guilds()]

        await self.sync_command()

        # This copies the global commands over to your guild.
        await asyncio.gather(*[self.sync_command(guild) for guild in guilds])

        await self.db.get_guilds(guilds)

    async def sync_command(self, guild: Optional[discord.Guild] = None):
        await self.tree.sync(guild=guild)
        log.info(f"Command synced to: {guild or 'Global'}")

    async def add_cogs(self):
        files = sorted(glob(f"neonbot{sep}cogs{sep}[!_]*.py"))
        extensions = [re.split(r"[{0}.]".format(re.escape(sep)), file)[-2] for file in files]
        start_time = time()

        print(file=sys.stderr)

        for extension in extensions:
            log.info(f"Loading {extension} cog...")
            await self.load_extension("neonbot.cogs." + extension)

        print(file=sys.stderr)

        log.info(f"Loaded {len(extensions)} cogs after {(time() - start_time):.2f}s\n")

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

    async def update_presence(self):
        setting = await Setting.get_instance()

        await self.change_presence(
            activity=discord.Activity(
                name=setting.activity_name,
                type=discord.ActivityType[setting.activity_type]
            ),
            status=discord.Status[setting.status]
        )

    async def send_response(self, interaction: discord.Interaction, *args, **kwargs):
        if not interaction.response.is_done():
            await interaction.response.send_message(*args, **kwargs)
        elif interaction.response.type == discord.InteractionResponseType.deferred_message_update:
            await interaction.followup.send(*args, **kwargs)
        else:
            if 'view' not in kwargs:
                kwargs['view'] = None
            await interaction.edit_original_response(*args, **kwargs)

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

    async def close(self) -> None:
        from .classes.player import Player

        await asyncio.gather(*[player.clear_messages() for player in Player.servers.values()])
        await self.session.close()
        await super().close()

    async def start(self, *args, **kwargs) -> None:
        await super().start(*args, **kwargs)

    def run(self, *args, **kwargs):
        super().run(env.str('TOKEN'), *args, **kwargs)

    def _handle_ready(self) -> None:
        pass

    def set_ready(self):
        self._ready.set()
