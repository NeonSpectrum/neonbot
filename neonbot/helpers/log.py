import logging
import sys
from datetime import datetime
from typing import Any, Callable, Optional, Union

import discord
import termcolor
from discord.ext import commands
from pytz import timezone

from ..env import env
from .constants import LOG_FORMAT, TIMEZONE


def colored(*args: Any) -> str:
    if env.bool("HEROKU", False):
        return args[0]
    return termcolor.colored(*args)


def cprint(*args: Any) -> None:
    if env.bool("HEROKU", False):
        print(args[0])
    termcolor.cprint(*args)

class Formatter(logging.Formatter):
    def converter(self, timestamp):
        dt = datetime.datetime.fromtimestamp(timestamp)
        return timezone(TIMEZONE).localize(dt)

    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            try:
                s = dt.isoformat(timespec='milliseconds')
            except TypeError:
                s = dt.isoformat()
        return s

class Log(logging.Logger):
    def __init__(self, *args: Any, **kwargs: Any):
        self._log: Callable
        super().__init__(*args, **kwargs)

        self.formatter = Formatter(LOG_FORMAT, "%Y-%m-%d %I:%M:%S %p")

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
        *,
        guild: Optional[discord.Guild] = None,
        channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None,
        user: Optional[discord.User] = None,
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
