import asyncio
import math
import random
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from pytz import timezone

from bot import bot
from helpers import log

from .constants import CHOICES_EMOJI, PAGINATION_EMOJI, TIMEZONE

date = lambda: datetime.now(timezone(TIMEZONE))
date_formatted = lambda: f"{date():%Y-%m-%d %-I:%M:%S %p}"


def Embed(**kwargs):
    return discord.Embed(color=0x59ABE3, **kwargs)


class PaginationEmbed:
    def __init__(self, array=[], authorized_users=[]):
        self.bot = bot
        self.array = array
        self.authorized_users = authorized_users

        self.index = 0
        self.embed = Embed()
        self.msg = None

    async def build(self, ctx):
        self.ctx = ctx
        self.title = self.embed.title
        await self._send()

        if len(self.array) > 1:
            asyncio.ensure_future(self._add_reactions())
            await self._listen()

    async def _send(self):
        embed = self.embed.copy()
        embed.description = (
            self.array[self.index].description
            + f"\n\n**Page {self.index+1}/{len(self.array)}**"
        )

        if self.msg:
            return await self.msg.edit(embed=embed)

        self.msg = await self.ctx.send(embed=embed)

    async def _listen(self):
        msg = self.msg

        def check(reaction, user):
            if not user.bot:
                asyncio.ensure_future(reaction.remove(user))
            return (
                reaction.emoji in PAGINATION_EMOJI
                and user.id in self.authorized_users
                and reaction.message.id == msg.id
            )

        while True:
            try:
                reaction, _ = await self.bot.wait_for(
                    "reaction_add", timeout=60, check=check
                )

                await self._execute_command(PAGINATION_EMOJI.index(reaction.emoji))

                if reaction.emoji == "🗑":
                    await self.msg.delete()

            except asyncio.TimeoutError:
                await msg.clear_reactions()
                break

    async def _add_reactions(self):
        for emoji in PAGINATION_EMOJI:
            try:
                await self.msg.add_reaction(emoji)
            except discord.NotFound:
                break

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


async def embed_choices(ctx, entries):
    if len(entries) == 0:
        return await ctx.send(embed=Embed(description="Empty choices."), delete_after=5)

    embed = Embed(title=f"Choose 1-{len(entries)} below.")

    for index, entry in enumerate(entries, start=1):
        embed.add_field(name=f"{index}. {entry.title}", value=entry.url, inline=False)

    msg = await ctx.send(embed=embed)

    async def react_to_msg():
        for emoji in CHOICES_EMOJI[0 : len(entries)] + [CHOICES_EMOJI[-1]]:
            try:
                await msg.add_reaction(emoji)
            except discord.NotFound:
                break

    try:
        asyncio.ensure_future(react_to_msg())
        reaction, _ = await bot.wait_for(
            "reaction_add",
            timeout=10,
            check=lambda reaction, user: reaction.emoji in CHOICES_EMOJI
            and ctx.author == user
            and reaction.message.id == msg.id,
        )
        if reaction.emoji == "🗑":
            raise asyncio.TimeoutError
    except asyncio.TimeoutError:
        await msg.delete()
        return -1
    else:
        await msg.delete()
        index = CHOICES_EMOJI.index(reaction.emoji)
        return index


def format_seconds(secs, format=0):
    formatted = str(timedelta(seconds=secs))
    if formatted.startswith("0:"):
        return formatted[2:]
    return formatted


def plural(val, singular, plural):
    return f"{val} {singular if val == 1 else plural}"


async def check_args(ctx, arg, choices):
    if arg in choices:
        return True
    await ctx.send(
        embed=Embed(description=f"Invalid argument. ({' | '.join(choices)})")
    )
    return False


def guess_string(string):
    string = list(string)

    i = 0
    while i < math.ceil(len(string) / 2):
        index = random.randint(0, len(string) - 1)
        if string[index] == " " or string[index] == "_":
            continue
        string[index] = "_"
        i += 1

    return " ".join(string)
