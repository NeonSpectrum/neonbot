from os import listdir, path, popen
from os.path import isfile, join
from time import time

import discord
from addict import Dict
from discord.ext import commands
from pymongo import MongoClient
from termcolor import cprint

from helpers.constants import LOGO
from helpers.database import Database, load_database
from main import env

uptime = time()
servers = Dict({"music": {}})
bot = commands.Bot(command_prefix=lambda bot, message: Database(message.guild.id).config.prefix,
                   owner_ids=env.list("OWNER_ID", subcast=int))


def load_cogs():
  cogs_dir = "modules"
  for extension in [
      f.replace('.py', '') for f in listdir("src/" + cogs_dir) if isfile(join("src/" + cogs_dir, f))
  ]:
    bot.load_extension(cogs_dir + "." + extension)


def run():
  cprint(LOGO, 'blue')
  load_database()
  load_cogs()
  bot.run(env("TOKEN"))
