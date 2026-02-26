import logging
import sys
from typing import Any, Callable, Optional, Union, TYPE_CHECKING

import coloredlogs
import discord
from discord.ext import commands

from neonbot.env import BOT_LOG_LEVEL
from neonbot.utils.constants import LOG_FORMAT

if TYPE_CHECKING:
    from neonbot import NeonBot


class Log(logging.Logger):
    def __init__(self, *args: Any, **kwargs: Any):
        self._log: Callable
        super().__init__(*args, **kwargs)

        self.set_file_handler()
        self.set_console_handler()

    def set_file_handler(self) -> None:
        file = logging.FileHandler(filename='debug.log', encoding='utf-8', mode='a')
        file.setFormatter(logging.Formatter(LOG_FORMAT, '%Y-%m-%d %I:%M:%S %p'))
        file.setLevel(logging.DEBUG)
        self.addHandler(file)

    def set_console_handler(self) -> None:
        level_styles = {
            'debug': {'color': 'cyan'},
            'info': {'color': 'white'},
            'warning': {'color': 'yellow'},
            'error': {'color': 'red'},
            'critical': {'color': 'red'}
        }

        field_styles = {
            'asctime': {'color': 'white'},
            'levelname': {'bold': True},
            'module': {'color': 'blue'},
            'funcName': {'color': 'green'},
            'lineno': {'color': 'yellow'}
        }

        formatter = coloredlogs.ColoredFormatter(LOG_FORMAT, '%Y-%m-%d %I:%M:%S %p', field_styles=field_styles, level_styles=level_styles)
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.setLevel(BOT_LOG_LEVEL)
        self.addHandler(console)

    def cmd(
        self,
        ctx: Union[commands.Context['NeonBot'], discord.Interaction['NeonBot']],
        msg: str,
        *,
        guild: Optional[discord.Guild] = None,
        channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None,
        user: Optional[Union[str, int, discord.User]] = None,
    ) -> None:
        guild = guild or ctx.guild
        channel = channel or ctx.channel

        if not user:
            if isinstance(ctx, commands.Context):
                user = ctx.author
            elif isinstance(ctx, discord.Interaction):
                user = ctx.user
        elif isinstance(user, int):
            user = ctx.bot.get_user(user)

        print(file=sys.stderr)
        self._log(
            logging.INFO,
            f"""
    Guild: {guild}
    Channel: {channel}
    User: {user}
    Message: {str(msg)}""",
            (),
        )
