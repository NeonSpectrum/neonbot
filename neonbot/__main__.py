import logging
import os

import discord

from helpers.constants import LOG_FORMAT

if __name__ == "__main__":
    import bot

    logger = logging.getLogger("discord")
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename="debug.log", encoding="utf-8", mode="w")
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)

    if not discord.opus.is_loaded():
        discord.opus.load_opus("lib/libopus.so.0")

    if os.name == "nt":
        os.system("color")

    bot.run()
