from os import listdir, path, popen
from os.path import isfile, join
from time import time

import discord
from addict import Dict
from aiohttp import ClientSession
from discord.ext import commands
from environs import Env
from pymongo import MongoClient
from termcolor import cprint

from helpers.constants import LOGO, NAME, VERSION

env = Env()
env.read_env()
owner_ids = env.list("OWNER_IDS", [], subcast=int)
bot = commands.Bot(
    command_prefix=env("DEFAULT_PREFIX"),
    owner_ids=set(owner_ids),
    help_command=commands.DefaultHelpCommand(verify_checks=False),
)


@bot.check
async def globally_block_dms(ctx):
    return ctx.guild is not None


def load_cogs():
    cogs_dir = "neonbot/cogs"
    for extension in [
        f.replace(".py", "")
        for f in listdir(cogs_dir)
        if f != "__init__.py" and isfile(join(cogs_dir, f))
    ]:
        bot.load_extension("cogs." + extension)


def run():
    from helpers.database import Database, load_database
    from helpers import log

    bot.command_prefix = lambda bot, message: Database(message.guild.id).config.prefix
    bot.session = ClientSession(loop=bot.loop)

    cprint(LOGO, "blue")
    log.info(f"Starting {NAME} v{VERSION}")
    load_database()
    load_cogs()
    bot.run(env("TOKEN"))

    bot.session.close()
