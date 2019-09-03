from termcolor import colored, cprint

from bot import env
from helpers.constants import TIMEZONE
from helpers.utils import date_formatted

if env.bool("HEROKU", False):
    colored = lambda msg, color: msg


def cmd(ctx, *msg, guild=None, channel=None, user=None):
    print(
        f"""
{colored(f"------{date_formatted()}------", "yellow")}
    {colored('Guild', 'cyan')}: {guild or ctx.guild}
    {colored('Channel', 'cyan')}: {channel or ctx.channel}
    {colored('User', 'cyan')}: {user or ctx.author}
    {colored('Message', 'cyan')}: {' '.join(map(str,msg))}
"""
    )


def info(*msg):
    print(
        f"{colored(date_formatted(), 'yellow')} | {colored(' '.join(map(str,msg)), 'cyan')}"
    )


def warn(*msg):
    print(
        f"{colored(date_formatted(), 'yellow')} | {colored(' '.join(map(str,msg)), 'red')}"
    )
