import asyncio

import discord

from .. import bot
from .constants import CHOICES_EMOJI


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


async def send_to_all_owners(*args, excluded=[], **kwargs):
    for owner in filter(lambda x: x not in excluded, bot.owner_ids):
        await bot.get_user(owner).send(*args, **kwargs)
