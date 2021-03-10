#!/usr/bin/env python3

import os

from discord import opus

from neonbot import bot


def main() -> None:
    if not opus.is_loaded():
        opus.load_opus("./lib/libopus.so.0")

    if os.name == "nt":
        os.system("color")

    os.makedirs("./tmp/youtube_dl", exist_ok=True)

    bot.run()


if __name__ == "__main__":
    main()
