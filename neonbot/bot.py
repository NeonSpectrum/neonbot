from os import listdir, path, popen
from os.path import isfile, join

import discord
from addict import Dict
from aiohttp import ClientSession
from discord.ext import commands
from pymongo import MongoClient
from termcolor import cprint

from . import Database, __title__, __version__, env
from .helpers import log
from .helpers.constants import LOGO


class Bot(commands.Bot):
    def __init__(self):
        self.owner_ids = env.list("OWNER_IDS", [], subcast=int)
        super().__init__(
            command_prefix=env("DEFAULT_PREFIX"),
            owner_ids=set(self.owner_ids),
            help_command=commands.DefaultHelpCommand(verify_checks=False),
        )
        self.db = Database()
        self.session = ClientSession(loop=self.loop)

        log.init()

    @staticmethod
    async def globally_block_dms(ctx):
        return ctx.guild is not None

    def load_cogs(self):
        cogs_dir = "neonbot/cogs"
        for extension in [
            f.replace(".py", "")
            for f in listdir(cogs_dir)
            if f != "__init__.py" and isfile(join(cogs_dir, f))
        ]:
            self.load_extension("neonbot.cogs." + extension)

    def run(self):
        cprint(LOGO, "blue")
        log.info(f"Starting {__title__} v{__version__}")

        self.db.load_database()
        self.command_prefix = lambda bot, message: self.db.get_guild(
            message.guild.id
        ).config.prefix

        self.add_check(self.globally_block_dms)

        self.load_cogs()
        super().run(env("TOKEN"))


bot = Bot()
