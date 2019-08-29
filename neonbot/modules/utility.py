import os
import random
from time import time

import psutil
from addict import Dict
from aiohttp import ClientSession
from discord.ext import commands

from bot import bot, uptime
from helpers.constants import AUTHOR, NAME, VERSION
from helpers.utils import Embed, format_seconds


async def chatbot(user_id, message):
  session = ClientSession()
  res = await session.get("https://program-o.com/v3/chat.php", params={"say": message})
  json = await res.json()
  await session.close()
  return Dict()


class Utility(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.command()
  async def random(self, ctx, *args):
    await ctx.send(embed=Embed(description=random.choice(args)))

  @commands.command(aliases=["stats"])
  async def status(self, ctx):
    from .event import get_commands_executed

    process = psutil.Process(os.getpid())

    embed = Embed()
    embed.set_author(name=f"{NAME} v{VERSION}", icon_url=bot.user.avatar_url)
    embed.add_field(name="Username", value=bot.user.name)
    embed.add_field(name="Created On", value=f"{bot.user.created_at:%Y-%m-%d %I:%M:%S %p}")
    embed.add_field(name="Created By", value=AUTHOR)
    embed.add_field(name="Guilds", value=len(bot.guilds))
    embed.add_field(name="Channels", value=sum(1 for _ in bot.get_all_channels()))
    embed.add_field(name="Users", value=len(bot.users))
    embed.add_field(name="Commands Executed", value=get_commands_executed())
    embed.add_field(name="Ram Usage",
                    value=f"Approximately {(process.memory_info().rss / 1024000):.2f} MB",
                    inline=True)
    embed.add_field(name="Uptime", value=format_seconds(time() - uptime).split(".")[0])

    await ctx.send(embed=embed)


def setup(bot):
  bot.add_cog(Utility(bot))
