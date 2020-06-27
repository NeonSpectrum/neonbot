import json
import logging
import os
import re
import sys
from glob import glob
from os import path
from time import time
from typing import Any, Callable, List, Tuple, Union, cast

import discord
import psutil
from addict import Dict
from aiohttp import ClientSession, ClientTimeout
from discord.ext import commands
from discord.utils import oauth_url

from . import __title__, __version__
from .classes import Embed
from .database import Database
from .env import env
from .helpers.constants import LOGO, PERMISSIONS
from .helpers.log import Log, cprint

log = cast(Log, logging.getLogger(__name__))


class Bot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix=self.get_command_prefix())

        self.start_message()

        self.env = env
        self.db = Database()
        self.default_prefix = env.str("DEFAULT_PREFIX", ".")
        self.owner_ids = set(env.list("OWNER_IDS", [], subcast=int))

        self.status, self.activity = self.get_presence()
        self.session = ClientSession(loop=self.loop, timeout=ClientTimeout(total=30))
        self.user_agent = f"NeonBot v{__version__}"

        self.app_info: discord.AppInfo = None
        self.set_storage()
        self.load_music()

    def set_storage(self) -> None:
        self.commands_executed: List[str] = []
        self.game = Dict()
        self.music = Dict()
        self._music_cache = Dict()

    def load_music(self) -> None:
        file = "./tmp/music.json"
        if path.exists(file):
            with open(file, "r") as f:
                self._music_cache = Dict(json.load(f))
            os.remove(file)

    def save_music(self) -> None:
        file = "./tmp/music.json"
        with open(file, "w") as f:
            cache = Dict()
            for key, player in self.music.items():
                cache[key] = {
                    "current_queue": player.current_queue,
                    "queue": [
                        {**queue, "requested": queue.requested.id}
                        for queue in player.queue
                    ],
                }
            json.dump(cache, f, indent=4)

    def start_message(self) -> None:
        cprint(LOGO, "blue")
        log.info(f"Starting {__title__} v{__version__}")

    def get_presence(self) -> Tuple[discord.Status, discord.Activity]:
        settings = self.db.get_settings().settings
        activity_type = settings.game.type.lower()
        activity_name = settings.game.name
        status = settings.status

        return (
            discord.Status[status],
            discord.Activity(
                name=activity_name, type=discord.ActivityType[activity_type]
            ),
        )

    async def fetch_app_info(self) -> None:
        if not self.app_info:
            self.app_info = await self.application_info()

    def get_command_prefix(self) -> Union[Callable, str]:
        return (
            lambda _, message: self.db.get_guild(message.guild.id).config.prefix
            if message.guild
            else self.default_prefix
        )

    def load_cogs(self) -> None:
        files = sorted(glob("neonbot/cogs/[!_]*.py"))
        extensions = list(map(lambda x: re.split(r"[/.]", x)[-2], files))
        start_time = time()

        print(file=sys.stderr)

        for extension in extensions:
            log.info(f"Loading {extension} cog...")
            self.load_extension("neonbot.cogs." + extension)

        print(file=sys.stderr)

        log.info(f"Loaded {len(extensions)} cogs after {(time() - start_time):.2f}s")

    async def logout(self) -> None:
        await self.session.close()
        await self.http.close()
        for voice in list(self.voice_clients).copy():
            await voice.disconnect(force=True)

    async def restart(self) -> None:
        await self.logout()
        try:
            p = psutil.Process(os.getpid())
            for handler in p.open_files() + p.connections():
                os.close(handler.fd)
        except Exception as e:
            log.exception(e)
        else:
            python = sys.executable
            os.execl(python, python, *sys.argv)

    async def send_restart_message(self) -> None:
        file = "./tmp/restart_config.json"
        if path.exists(file):
            with open(file, "r") as f:
                data = Dict(json.load(f))
            os.remove(file)

            channel = self.get_channel(data.channel_id)
            try:
                message = await channel.fetch_message(data.message_id)
            except discord.NotFound:
                pass
            else:
                await self.delete_message(message)
            await channel.send(embed=Embed("Bot Restarted."), delete_after=10)

    async def send_invite_link(self, channel: discord.DMChannel) -> None:
        with channel.typing():
            url = oauth_url(
                self.app_info.id, discord.Permissions(permissions=PERMISSIONS)
            )
            await channel.send(f"Bot invite link: {url}")
            log.info(f"Sent an invite link to: {channel.recipient}")

    async def send_to_all_owners(
        self, *args: Any, excluded: list = [], **kwargs: Any
    ) -> None:
        for owner in filter(lambda x: x not in excluded, self.owner_ids):
            await self.get_user(owner).send(*args, **kwargs)

    async def delete_message(self, message: discord.Message) -> None:
        if not isinstance(message, discord.Message):
            return

        try:
            await message.delete()
        except discord.NotFound as e:
            log.exception(e)

    def run(self) -> None:
        self.load_cogs()
        super().run(env.str("TOKEN"))
