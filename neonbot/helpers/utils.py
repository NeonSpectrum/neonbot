import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from pytz import timezone

from helpers import log

from .constants import PAGINATION_EMOJI, TIMEZONE

date = lambda: datetime.now(timezone(TIMEZONE))
date_formatted = lambda: f"{date():%Y-%m-%d %-I:%M:%S %p}"


def Embed(**kwargs):
  return discord.Embed(color=0x59abe3, **kwargs)


class PaginationEmbed:
  index = 0
  embed = Embed()
  msg = None

  def __init__(self, bot, array=[], authorized_users=[]):
    self.bot = bot
    self.array = array
    self.authorized_users = authorized_users

  async def build(self, ctx):
    self.ctx = ctx
    await self._send()

    if len(self.array) > 1:
      asyncio.ensure_future(self._add_reactions())
      await self._listen()

  async def _send(self):
    embed = self.embed.copy()
    embed.description = self.array[self.index].description

    if self.msg:
      return await self.msg.edit(embed=embed)

    self.msg = await self.ctx.send(embed=embed)

  async def _listen(self):
    msg = self.msg

    def check(reaction, user):
      if not user.bot:
        asyncio.ensure_future(reaction.remove(user))
      return reaction.emoji in PAGINATION_EMOJI and user.id in self.authorized_users and reaction.message.id == msg.id

    while True:
      try:
        reaction, user = await self.bot.wait_for("reaction_add", timeout=60, check=check)

        await self._execute_command(PAGINATION_EMOJI.index(reaction.emoji))

        if reaction.emoji == "🗑":
          raise asyncio.TimeoutError

      except asyncio.TimeoutError:
        await msg.clear_reactions()
        break

  async def _add_reactions(self):
    self.reactions = []
    for emoji in PAGINATION_EMOJI:
      try:
        self.reactions.append(await self.msg.add_reaction(emoji))
      except discord.NotFound:
        self.reactions = []
        return

  async def _execute_command(self, cmd):
    current_index = self.index

    if cmd == 0 and self.index > 0:
      self.index -= 1
    elif cmd == 1 and self.index < len(self.array) - 1:
      self.index += 1

    if current_index != self.index:
      await self._send()

  def set_author(self, **kwargs):
    self.embed.set_author(**kwargs)

  def set_footer(self, **kwargs):
    self.embed.set_footer(**kwargs)


def format_seconds(secs, format=0):
  formatted =  str(timedelta(seconds=secs))
  if formatted.startswith("0:"):
    return formatted[2:]
  return formatted


def plural(val, singular, plural):
  return f"{val} {singular if val == 1 else plural}"
