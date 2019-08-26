from os import getenv

import arrow
from termcolor import colored, cprint

from helpers.constants import TIMEZONE

date = lambda: arrow.now(TIMEZONE).format("YYYY-MM-DD hh:mm:ss A")

if not getenv("HEROKU"):
  colored = lambda msg, color: msg


def cmd(ctx, *msg):
  print(f"""
{colored(f"------{date()}------", "yellow")}
  {colored('Guild', 'cyan')}: {ctx.guild}
  {colored('Channel', 'cyan')}: {ctx.channel}
  {colored('User', 'cyan')}: {ctx.author}
  {colored('Message', 'cyan')}: {' '.join(map(str,msg))}
""")


def info(*msg):
  print(f"{colored(date(), 'yellow')} | {colored(' '.join(map(str,msg)), 'cyan')}")


def warn(*msg):
  print(f"{colored(date(), 'yellow')} | {colored(' '.join(map(str,msg)), 'red')}")
