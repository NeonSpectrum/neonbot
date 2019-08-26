from os import listdir, path, popen
from os.path import isfile, join

import discord
from addict import Dict
from discord.ext import commands
from pymongo import MongoClient
from termcolor import cprint

from helpers.constants import LOGO
from helpers.database import Database, load_database
from main import env

bot = None
servers = Dict()


def prefix(bot, message):
  config = Database(message.guild.id).config
  return config.prefix


def load_cogs():
  cogs_dir = "modules"
  for extension in [f.replace('.py', '') for f in listdir(cogs_dir) if isfile(join(cogs_dir, f))]:
    bot.load_extension(cogs_dir + "." + extension)


def run():
  global bot
  bot = commands.Bot(command_prefix=prefix, owner_ids=env.list("OWNER_ID", subcast=int))
  cprint(LOGO, 'blue')
  load_database()
  load_cogs()
  bot.run(env("TOKEN"))
