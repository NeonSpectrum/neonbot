import asyncio
import math

import discord
from discord.ext import commands

from bot import bot
from helpers import log

from .constants import PAGINATION_EMOJI
from .database import db


def Embed(**kwargs):
  return discord.Embed(color=0x59abe3, **kwargs)


class PaginationEmbed:
  index = 0
  embed = Embed()
  msg = None

  def __init__(self, array=[], authorized_users=[]):
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
        reaction, user = await bot.wait_for("reaction_add", timeout=60, check=check)

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
  secNum = int(secs)
  hours = math.floor(secNum / 3600)
  minutes = math.floor((secNum - hours * 3600) / 60)
  seconds = secNum - hours * 3600 - minutes * 60

  if hours < 10:
    hours = f"0{hours}"
  if minutes < 10:
    minutes = f"0{minutes}"
  if seconds < 10:
    seconds = f"0{seconds}"

  if format == 0:
    time = f"{hours}:{minutes}:{seconds}"
    if hours == '00':
      time = time[3:]
    return time
  elif format == 3:
    return f"{hours}:{minutes}:{seconds}"
  elif format == 2:
    minutes = int(hours) * 60 + int(minutes)
    return ('0' + minutes if minutes < 10 else minutes) + ':' + seconds
  elif format == 1:
    seconds = int(hours) * 60 + int(minutes) * 60 + int(seconds)
    return '0' + seconds if seconds < 10 else seconds


def raise_and_send(ctx, msg, exception=commands.CommandError):
  asyncio.ensure_future(ctx.send(embed=Embed(description=msg)))
  log.cmd(ctx, msg)
  raise exception(msg)


def plural(val, singular, plural):
  return f"{val} {singular if val == 1 else plural}"
