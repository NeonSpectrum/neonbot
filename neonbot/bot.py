from os import listdir, path, popen
from os.path import isfile, join
from time import time

import discord
from addict import Dict
from discord.ext import commands
from pymongo import MongoClient
from termcolor import cprint

from __main__ import env
from helpers import log
from helpers.constants import LOGO, NAME, VERSION
from helpers.database import Database, load_database

uptime = time()
bot = commands.Bot(command_prefix=lambda bot, message: Database(message.guild.id).config.prefix,
                   owner_ids=env.list("OWNER_IDS", [], subcast=int))


def load_cogs():
  cogs_dir = "neonbot/modules"
  for extension in [f.replace('.py', '') for f in listdir(cogs_dir) if isfile(join(cogs_dir, f))]:
    bot.load_extension("modules." + extension)


def run():
  cprint(LOGO, 'blue')
  log.info(f"Starting {NAME} v{VERSION}")
  load_database()
  load_cogs()
  bot.run(env("TOKEN"))
