import json
import logging
import os
import sys
from os import path
from typing import Callable, List, Union, cast

import discord
import psutil
from addict import Dict
from aiohttp import ClientSession, ClientTimeout
from discord.ext import commands
from discord.utils import oauth_url

from . import Database, __title__, __version__, env
from .helpers.constants import LOGO, PERMISSIONS
from .helpers.log import Log, cprint

log = cast(Log, logging.getLogger(__name__))


class Bot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix=self.get_command_prefix())

        self.start_message()

        self.db = Database()
        self.default_prefix = env.str("DEFAULT_PREFIX", ".")
        self.owner_ids = set(env.list("OWNER_IDS", [], subcast=int))

        self.activity = self.get_activity()
        self.session = ClientSession(loop=self.loop, timeout=ClientTimeout(total=30))

        self.app_info: discord.AppInfo = None
        self.commands_executed: List[str] = []

        self.game = Dict()
        self.music = Dict()

        self._music_cache = Dict()
        self.load_music()

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

    def get_activity(self) -> discord.Activity:
        settings = self.db.get_settings().settings
        activity_type = settings.game.type.lower()
        activity_name = settings.game.name
        status = settings.status

        return discord.Activity(
            name=activity_name,
            type=discord.ActivityType[activity_type],
            status=discord.Status[status],
        )

    async def fetch_app_info(self) -> None:
        if not self.app_info:
            self.app_info = await bot.application_info()

    def get_command_prefix(self) -> Union[Callable, str]:
        return (
            lambda _, message: self.db.get_guild(message.guild.id).config.prefix
            if message.guild
            else self.default_prefix
        )

    def load_cogs(self) -> None:
        cogs_dir = "neonbot/cogs"
        excluded = "__init__.py"
        for extension in [
            f.replace(".py", "")
            for f in os.listdir(cogs_dir)
            if f not in excluded and path.isfile(path.join(cogs_dir, f))
        ]:
            self.load_extension("neonbot.cogs." + extension)

    async def logout(self) -> None:
        await self.session.close()
        super().logout()

    async def restart(self) -> None:
        await self.session.close()
        [await voice.disconnect() for voice in self.voice_clients]
        try:
            p = psutil.Process(os.getpid())
            for handler in p.open_files() + p.connections():
                os.close(handler.fd)
        except Exception as e:
            log.exception(e)

        python = sys.executable
        os.execl(python, python, *sys.argv)

    async def send_restart_message(self) -> None:
        from .helpers.utils import Embed

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
                await message.delete()
            await channel.send(embed=Embed("Bot Restarted."), delete_after=10)

    async def send_invite_link(self, channel: discord.DMChannel) -> None:
        with channel.typing():
            url = oauth_url(
                self.app_info.id, discord.Permissions(permissions=PERMISSIONS)
            )
            await channel.send(f"Bot invite link: {url}")
            log.info(f"Sent an invite link to: {channel.recipient}")

    def run(self) -> None:
        self.load_cogs()
        super().run(env.str("TOKEN"))


bot = Bot()
