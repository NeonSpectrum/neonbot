import logging
import os

import discord
from environs import Env

from helpers.constants import LOG_FORMAT

env = Env()

if __name__ == '__main__':
  from bot import run

  formatter = logging.Formatter(LOG_FORMAT)

  logger = logging.getLogger('discord')
  logger.setLevel(logging.INFO)
  handler = logging.FileHandler(filename='debug.log', encoding='utf-8', mode='w')
  handler.setFormatter(formatter)
  logger.addHandler(handler)

  if os.name == "nt":
    os.system('color')

  env.read_env()
  run()
