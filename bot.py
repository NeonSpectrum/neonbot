from os import getenv, listdir
from os.path import isfile, join

import discord
from addict import Dict
from discord.ext import commands
from pymongo import MongoClient
from termcolor import cprint

from helpers import database, log
from helpers.constants import LOGO
from helpers.database import load_database

bot = None
servers = Dict()


def prefix(bot, message):
  id = message.guild.id
  return getenv("PREFIX")


def load_cogs():
  cogs_dir = "modules"
  for extension in [f.replace('.py', '') for f in listdir(cogs_dir) if isfile(join(cogs_dir, f))]:
    bot.load_extension(cogs_dir + "." + extension)


def run():
  global bot
  bot = commands.Bot(command_prefix=prefix, owner_id=int(getenv("OWNER_ID")))
  cprint(LOGO, 'blue')
  load_database()
  load_cogs()
  bot.run(getenv("TOKEN"))
