import random
from io import BytesIO

import discord
import requests
from addict import Dict
from discord.ext import commands

from bot import bot, env
from helpers.utils import Embed


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

  @commands.command(aliases=["dict"])
  async def dictionary(self, ctx, *, args):
    msg = await ctx.send(embed=Embed(description="Searching..."))
    res = requests.get(f"https://www.dictionaryapi.com/api/v3/references/sd4/json/{args}",
                       params={"key": env("DICTIONARY_API")})

    if not isinstance(res.json()[0], dict):
      await msg.delete()
      return await ctx.send(embed=Embed(description="Term not found."))

    dictionary = Dict(res.json()[0])
    prs = dictionary.hwi.prs[0] or dictionary.vrs[0].prs[0]
    audio = prs.sound.audio
    if audio:
      url = f"https://media.merriam-webster.com/soundc11/{audio[0]}/{audio}.wav"
      res = requests.get(url, stream=True)

    embed = Embed(description=f"[🔉 Play audio]({url})" if url else None)
    embed.add_field(name=args, value=f"*{prs.mw}*" + "\n" + dictionary.shortdef[0])
    embed.set_author(name="Merriam-Webster Dictionary",
                     icon_url="https://dictionaryapi.com/images/MWLogo.png")
    embed.set_footer(text=f"Searched by {ctx.author}", icon_url=ctx.author.avatar_url)

    await msg.delete()
    await ctx.send(embed=embed)
    if audio:
      await ctx.send(file=discord.File(BytesIO(res.content), args + ".wav"))


def setup(bot):
  bot.add_cog(Search(bot))
