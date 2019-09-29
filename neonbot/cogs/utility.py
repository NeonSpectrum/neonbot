import logging
import os
import random
from time import time
from typing import cast

import discord
import psutil
from addict import Dict
from discord.ext import commands

from .. import __author__, __title__, __version__, bot
from ..helpers.date import format_seconds
from ..helpers.log import Log
from ..helpers.utils import Embed

log = cast(Log, logging.getLogger(__name__))


async def chatbot(message: discord.Message, dm: bool = False) -> None:
    with message.channel.typing():
        msg = message.content if dm else " ".join(message.content.split(" ")[1:])
        res = await bot.session.get(
            "https://program-o.com/v3/chat.php", params={"say": msg}
        )
        response = Dict(await res.json())
        await message.channel.send(
            embed=Embed(
                f"{'' if dm else message.author.mention} {response.conversation.say.bot}"
            )
        )


class Utility(commands.Cog):
    @commands.command()
    async def chatbot(self, ctx: commands.Context) -> None:
        """Chat with a bot using program-o."""

        await chatbot(ctx.message)

    @commands.command()
    async def random(self, ctx: commands.Context, *args: str) -> None:
        """Picks a text in the given list."""

        await ctx.send(embed=Embed(random.choice(args)))

    @commands.command()
    async def say(self, ctx: commands.Context, *, text: str) -> None:
        """Says the text given."""

        await ctx.send(embed=Embed(text))

    @commands.command()
    async def speak(self, ctx: commands.Context, *, text: str) -> None:
        """Says the text given with TTS."""

        await ctx.send(text, tts=True, delete_after=0)

    @commands.command(aliases=["stats"])
    async def status(self, ctx: commands.Context) -> None:
        """Shows the information of the bot."""

        process = psutil.Process(os.getpid())

        embed = Embed()
        embed.set_author(
            name=f"{__title__} v{__version__}", icon_url=bot.user.avatar_url
        )
        embed.add_field(name="Username", value=bot.user.name)
        embed.add_field(
            name="Created On", value=f"{bot.user.created_at:%Y-%m-%d %I:%M:%S %p}"
        )
        embed.add_field(name="Created By", value=__author__)
        embed.add_field(name="Guilds", value=len(bot.guilds))
        embed.add_field(name="Channels", value=sum(1 for _ in bot.get_all_channels()))
        embed.add_field(name="Users", value=len(bot.users))
        embed.add_field(name="Commands Executed", value=len(bot.commands_executed))
        embed.add_field(
            name="Ram Usage",
            value=f"Approximately {(process.memory_info().rss / 1024000):.2f} MB",
            inline=True,
        )
        embed.add_field(
            name="Uptime",
            value=format_seconds(time() - process.create_time()).split(".")[0],
        )

        await ctx.send(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Utility())
