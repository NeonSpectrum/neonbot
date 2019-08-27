import logging
import os

import discord
from environs import Env

from helpers.constants import LOG_FORMAT

env = Env()

if __name__ == '__main__':
  from bot import run

  env.read_env()

  formatter = logging.Formatter(LOG_FORMAT)

  logger = logging.getLogger('discord')
  logger.setLevel(logging.INFO)
  handler = logging.FileHandler(filename='debug.log', encoding='utf-8', mode='w')
  handler.setFormatter(formatter)
  logger.addHandler(handler)

  if not discord.opus.is_loaded():
    discord.opus.load_opus("lib/libopus.so.0")

  if os.name == "nt":
    os.system('color')

  run()
