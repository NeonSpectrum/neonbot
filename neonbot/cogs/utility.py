import logging
import os
import random
from time import time
from typing import cast

import discord
import emoji
import psutil
import youtube_dl
from addict import Dict
from discord.ext import commands

from .. import __author__, __title__, __version__, bot, env
from ..classes import Embed
from ..helpers.date import format_seconds
from ..helpers.log import Log

log = cast(Log, logging.getLogger(__name__))


async def chatbot(message: discord.Message, dm: bool = False) -> None:
    if message.author.id not in bot.owner_ids:
        return

    with message.channel.typing():
        msg = message.content if dm else " ".join(message.content.split(" ")[1:])
        params = {
            "key": env.str('CLEVERBOT_API'),
            "input": emoji.demojize(msg)
        }

        if message.author.id in bot.chatbot and bot.chatbot[message.author.id]['time'] + 60 > time():
            params['cs'] = bot.chatbot[message.author.id]['cs']

        res = await bot.session.get(
            "https://www.cleverbot.com/getreply", params=params
        )
        response = Dict(await res.json())

        bot.chatbot[message.author.id] = {
            "cs": response.cs,
            "time": time()
        }
        await message.channel.send(
            embed=Embed(
                f"{'' if dm else message.author.mention} {response.output}"
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
        embed.set_author(f"{__title__} v{__version__}", icon_url=bot.user.avatar_url)
        embed.add_field("Username", bot.user.name)
        embed.add_field("Created On", f"{bot.user.created_at:%Y-%m-%d %I:%M:%S %p}")
        embed.add_field("Created By", __author__)
        embed.add_field("Guilds", len(bot.guilds))
        embed.add_field("Channels", sum(1 for _ in bot.get_all_channels()))
        embed.add_field("Users", len(bot.users))
        embed.add_field("Commands Executed", len(bot.commands_executed))
        embed.add_field(
            "Ram Usage",
            f"Approximately {(process.memory_info().rss / 1024000):.2f} MB",
            inline=True,
        )
        embed.add_field(
            "Uptime", format_seconds(time() - process.create_time()).split(".")[0]
        )
        embed.add_field(
            "Packages",
            f"""
            Discord.py: {discord.__version__}
            YoutubeDL: {youtube_dl.version.__version__}
            """
        )

        await ctx.send(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Utility())
