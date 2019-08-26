import logging
import os

import discord
from dotenv import load_dotenv

from bot import run
from helpers.constants import LOG_FORMAT


def load_env():
  if (not os.path.isfile('.env')):
    os.popen('cp .env.example .env')

  load_dotenv()


if __name__ == '__main__':
  formatter = logging.Formatter(LOG_FORMAT)

  logger = logging.getLogger('discord')
  logger.setLevel(logging.INFO)
  handler = logging.FileHandler(filename='debug.log', encoding='utf-8', mode='w')
  handler.setFormatter(formatter)
  logger.addHandler(handler)

  if os.name == "nt":
    os.system('color')

  load_env()
  run()
