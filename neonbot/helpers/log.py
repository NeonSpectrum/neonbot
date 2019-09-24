import logging
import sys
from typing import Callable, Union

import discord
import termcolor
from discord.ext import commands

from .. import env
from .constants import LOG_FORMAT


def colored(*args: str) -> str:
    if env.bool("HEROKU", False):
        return args[0]
    return termcolor.colored(*args)


def cprint(*args: str) -> None:
    if env.bool("HEROKU", False):
        print(args[0])
    termcolor.cprint(*args)


class Log(logging.Logger):
    def __init__(self, *args: str, **kwargs: str):
        self._log: Callable
        super().__init__(*args, **kwargs)

        self.formatter = logging.Formatter(LOG_FORMAT, "%Y-%m-%d %I:%M:%S %p")
        self.setLevel(
            env.log_level("LOG_LEVEL")
            if self.name.startswith("neonbot")
            else logging.ERROR
        )

        self.set_file_handler()
        self.set_console_handler()

    def set_file_handler(self) -> None:
        file = logging.FileHandler(filename="debug.log", encoding="utf-8", mode="w")
        file.setFormatter(self.formatter)
        self.addHandler(file)

    def set_console_handler(self) -> None:
        console = logging.StreamHandler()
        console.setFormatter(self.formatter)
        self.addHandler(console)

    def cmd(
        self,
        ctx: commands.Context,
        msg: str,
        guild: discord.Guild = None,
        channel: Union[discord.TextChannel, discord.VoiceChannel] = None,
        user: discord.User = None,
    ) -> None:
        guild = guild or ctx.guild
        channel = channel or ctx.channel
        user = user or ctx.author

        print(file=sys.stderr)
        self._log(
            logging.INFO,
            f"""
    Guild: {guild}
    Channel: {channel}
    User: {user}
    Message: {str(msg)}""",
            [],
        )


logging.setLoggerClass(Log)
