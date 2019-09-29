import asyncio
import logging
from typing import Any, cast

import discord
from discord.ext import commands

from ..helpers.log import Log
from .constants import CHOICES_EMOJI

log = cast(Log, logging.getLogger(__name__))


def Embed(description: Any = None, **kwargs: str) -> discord.Embed:
    return discord.Embed(
        color=0x59ABE3, description=description and str(description), **kwargs
    )


async def embed_choices(ctx: commands.Context, entries: list) -> int:
    if not entries:
        return await ctx.send(embed=Embed("Empty choices."), delete_after=5)

    embed = Embed(title=f"Choose 1-{len(entries)} below.")

    for index, entry in enumerate(entries, start=1):
        embed.add_field(name=f"{index}. {entry.title}", value=entry.url, inline=False)

    msg = await ctx.send(embed=embed)

    async def react_to_msg() -> None:
        for emoji in CHOICES_EMOJI[0 : len(entries)] + [CHOICES_EMOJI[-1]]:
            try:
                await msg.add_reaction(emoji)
            except discord.NotFound:
                break

    try:
        asyncio.ensure_future(react_to_msg())
        reaction, _ = await ctx.bot.wait_for(
            "reaction_add",
            timeout=10,
            check=lambda reaction, user: reaction.emoji in CHOICES_EMOJI
            and ctx.author == user
            and reaction.message.id == msg.id,
        )
        if reaction.emoji == "🗑":
            raise asyncio.TimeoutError
    except asyncio.TimeoutError:
        index = -1
    else:
        index = CHOICES_EMOJI.index(reaction.emoji)
    finally:
        await msg.delete()

    return index


def plural(val: int, singular: str, plural: str) -> str:
    return f"{val} {singular if val == 1 else plural}"


async def check_args(ctx: commands.Context, arg: str, choices: list) -> bool:
    if arg in choices:
        return True
    await ctx.send(embed=Embed(f"Invalid argument. ({' | '.join(choices)})"))
    return False
