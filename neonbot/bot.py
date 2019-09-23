import json
import logging
import os
import sys
from os import path

import discord
import psutil
from addict import Dict
from aiohttp import ClientSession, ClientTimeout
from discord.ext import commands

from . import Database, __title__, __version__, env
from .helpers.constants import LOGO
from .helpers.log import cprint

log = logging.getLogger(__name__)


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=self.get_command_prefix())

        self.start_message()

        self.db = Database()
        self.default_prefix = env("DEFAULT_PREFIX", ".")
        self.owner_ids = set(env.list("OWNER_IDS", [], subcast=int))

        self.activity = self.get_activity()
        self.session = ClientSession(loop=self.loop, timeout=ClientTimeout(total=30))

        self.app_info = None
        self.commands_executed = []

        self.game = Dict()
        self.music = Dict()

        self._music_cache = {}
        self.load_music()

    def load_music(self):
        file = "./tmp/music.json"
        if path.exists(file):
            with open(file, "r") as f:
                self._music_cache = Dict(json.load(f))
            os.remove(file)

    def save_music(self):
        file = "./tmp/music.json"
        with open(file, "w") as f:
            queue_list = Dict()
            for key, player in self.music.items():
                queue_list[key] = [
                    {**queue, "requested": queue.requested.id} for queue in player.queue
                ]
            json.dump(queue_list, f, indent=4)

    def start_message(self):
        cprint(LOGO, "blue")
        log.info(f"Starting {__title__} v{__version__}")

    def get_activity(self):
        settings = self.db.get_settings().settings
        activity_type = settings.game.type.lower()
        activity_name = settings.game.name
        status = settings.status

        return discord.Activity(
            name=activity_name,
            type=discord.ActivityType[activity_type],
            status=discord.Status[status],
        )

    async def set_app_info(self):
        self.app_info = await bot.application_info()

    def get_command_prefix(self):
        return (
            lambda _, message: self.db.get_guild(message.guild.id).config.prefix
            if message.guild
            else self.default_prefix
        )

    def load_cogs(self):
        cogs_dir = "neonbot/cogs"
        for extension in [
            f.replace(".py", "")
            for f in os.listdir(cogs_dir)
            if f != "__init__.py" and path.isfile(path.join(cogs_dir, f))
        ]:
            self.load_extension("neonbot.cogs." + extension)

    async def logout(self):
        await self.session.close()
        super().logout()

    async def restart(self):
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

    def run(self):
        self.load_cogs()
        super().run(env("TOKEN"))


bot = Bot()
