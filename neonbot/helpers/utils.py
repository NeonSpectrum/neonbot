import asyncio
import math
import random

import discord
from discord.ext import commands

from .. import bot
from ..helpers import log
from .constants import CHOICES_EMOJI, PAGINATION_EMOJI, TIMEZONE


def Embed(description=None, **kwargs):
    return discord.Embed(color=0x59ABE3, description=description, **kwargs)


async def embed_choices(ctx, entries):
    if len(entries) == 0:
        return await ctx.send(embed=Embed("Empty choices."), delete_after=5)

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


def plural(val, singular, plural):
    return f"{val} {singular if val == 1 else plural}"


async def check_args(ctx, arg, choices):
    if arg in choices:
        return True
    await ctx.send(embed=Embed(f"Invalid argument. ({' | '.join(choices)})"))
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
