import logging
from os import listdir
from os.path import isfile, join

from aiohttp import ClientSession
from discord.ext import commands

from . import Database, __title__, __version__, env
from .helpers.constants import LOGO
from .helpers.log import cprint

log = logging.getLogger(__name__)


class Bot(commands.Bot):
    def __init__(self):
        self.default_prefix = env("DEFAULT_PREFIX", ".")
        super().__init__(
            command_prefix=self.default_prefix, owner_ids=env.list("OWNER_IDS", [], subcast=int)
        )
        self.db = Database()
        self.session = ClientSession(loop=self.loop)
        self.commands_executed = 0

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
        self.command_prefix = (
            lambda bot, message: self.db.get_guild(message.guild.id).config.prefix
            if message.guild
            else self.default_prefix
        )

        self.load_cogs()
        super().run(env("TOKEN"))


bot = Bot()
