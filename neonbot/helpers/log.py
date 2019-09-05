import logging

from termcolor import colored, cprint

from .. import env
from .constants import LOG_FORMAT, TIMEZONE
from .date import date_format

if env.bool("HEROKU", False):
    colored = lambda msg, color: msg


def init():
    logger = logging.getLogger("discord")
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename="debug.log", encoding="utf-8", mode="w")
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)


def cmd(ctx, *msg, guild=None, channel=None, user=None):
    print(
        f"""
{colored(f"------{date_format()}------", "yellow")}
    {colored('Guild', 'cyan')}: {guild or ctx.guild}
    {colored('Channel', 'cyan')}: {channel or ctx.channel}
    {colored('User', 'cyan')}: {user or ctx.author}
    {colored('Message', 'cyan')}: {' '.join(map(str,msg))}
"""
    )


def info(*msg):
    print(
        f"{colored(date_format(), 'yellow')} | {colored(' '.join(map(str,msg)), 'cyan')}"
    )


def warn(*msg):
    print(
        f"{colored(date_format(), 'yellow')} | {colored(' '.join(map(str,msg)), 'red')}"
    )
