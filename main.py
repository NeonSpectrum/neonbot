import os

from discord import opus

from neonbot import bot


def main():
    if not opus.is_loaded():
        opus.load_opus("lib/libopus.so.0")

    if os.name == "nt":
        os.system("color")

    bot.run()


if __name__ == "__main__":
    main()
