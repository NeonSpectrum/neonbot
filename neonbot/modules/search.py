import random
from io import BytesIO

import discord
from addict import Dict
from aiohttp import ClientSession
from discord.ext import commands

from bot import bot, env
from helpers.utils import Embed


class Search(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.command()
  async def image(self, ctx, *, args):
    msg = await ctx.send(embed=Embed(description="Searching..."))
    session = ClientSession()
    res = await session.get("https://www.googleapis.com/customsearch/v1",
                            params={
                              "q": args,
                              "num": 1,
                              "searchType": "image",
                              "cx": env("GOOGLE_CX"),
                              "key": env("GOOGLE_API")
                            })
    image = Dict(await res.json())
    await session.close()

    embed = Embed()
    embed.set_author(name=f"Google Images for {args}", icon_url="http://i.imgur.com/G46fm8J.png")
    embed.set_footer(text=f"Searched by {ctx.author}")
    embed.set_image(url=image["items"][0].link)

    await msg.delete()
    await ctx.send(embed=embed)

  @commands.command(aliases=["dict"])
  async def dictionary(self, ctx, *, args):
    msg = await ctx.send(embed=Embed(description="Searching..."))
    session = ClientSession()
    res = await session.get(f"https://www.dictionaryapi.com/api/v3/references/sd4/json/{args}",
                            params={"key": env("DICTIONARY_API")})
    json = await res.json()
    if not isinstance(json[0], dict):
      await msg.delete()
      return await ctx.send(embed=Embed(description="Word not found."), delete_after=5)

    dictionary = Dict(json[0])
    prs = dictionary.hwi.prs[0] or dictionary.vrs[0].prs[0]
    audio = prs.sound.audio
    if audio:
      url = f"https://media.merriam-webster.com/soundc11/{audio[0]}/{audio}.wav"
      res = await session.get(url)

    embed = Embed()
    embed.add_field(name=args, value=f"*{prs.mw}*" + "\n" + dictionary.shortdef[0])
    embed.set_author(name="Merriam-Webster Dictionary",
                     icon_url="https://dictionaryapi.com/images/MWLogo.png")
    embed.set_footer(text=f"Searched by {ctx.author}", icon_url=ctx.author.avatar_url)

    await msg.delete()
    await ctx.send(embed=embed)
    if audio:
      content = await res.read()
      await ctx.send(file=discord.File(BytesIO(content), args + ".wav"))

    await session.close()


def setup(bot):
  bot.add_cog(Search(bot))
