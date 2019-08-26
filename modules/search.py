import random

import requests
from addict import Dict
from discord.ext import commands

from bot import bot
from helpers.utils import Embed
from main import env


class Search(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.command()
  async def image(self, ctx, *, args):
    msg = await ctx.send(embed=Embed(description="Searching..."))
    res = requests.get("https://www.googleapis.com/customsearch/v1",
                       params={
                         "q": args,
                         "num": 1,
                         "searchType": "image",
                         "cx": env("GOOGLE_CX"),
                         "key": env("GOOGLE_API")
                       })
    image = Dict(res.json())
    embed = Embed()
    embed.set_author(name=f"Google Images for {args}", icon_url="http://i.imgur.com/G46fm8J.png")
    embed.set_footer(text=f"Searched by {ctx.author}")
    embed.set_image(url=image["items"][0].link)

    await msg.delete()
    await ctx.send(embed=embed)


def setup(bot):
  bot.add_cog(Search(bot))
