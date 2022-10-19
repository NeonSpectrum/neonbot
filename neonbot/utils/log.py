import logging
import sys
from typing import Any, Callable, Optional, Union

import discord
from discord.ext import commands

from .constants import LOG_FORMAT


class Log(logging.Logger):
    def __init__(self, *args: Any, **kwargs: Any):
        self._log: Callable
        super().__init__(*args, **kwargs)

        self.formatter = logging.Formatter(LOG_FORMAT, "%Y-%m-%d %I:%M:%S %p")

        self.setLevel(
            logging.DEBUG
            if self.name.startswith("neonbot")
            else logging.ERROR
        )

        self.set_file_handler()
        self.set_console_handler()

    def set_file_handler(self) -> None:
        file = logging.FileHandler(filename="debug.log", encoding="utf-8", mode="a")
        file.setFormatter(self.formatter)
        self.addHandler(file)

    def set_console_handler(self) -> None:
        console = logging.StreamHandler()
        console.setFormatter(self.formatter)
        self.addHandler(console)

    def cmd(
        self,
        ctx: Union[commands.Context, discord.Interaction],
        msg: str,
        *,
        guild: Optional[discord.Guild] = None,
        channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None,
        user: Optional[Union[str, discord.User]] = None,
    ) -> None:
        guild = guild or ctx.guild
        channel = channel or ctx.channel

        if not user:
            if isinstance(ctx, commands.Context):
                user = ctx.author
            elif isinstance(ctx, discord.Interaction):
                user = ctx.user

        print(file=sys.stderr)
        self._log(
            logging.INFO,
            f"""
    Guild: {guild}
    Channel: {channel}
    User: {user}
    Message: {str(msg)}""",
            ()
        )
