import asyncio
from copy import deepcopy
from io import BytesIO

import discord
from addict import Dict
from discord.ext import commands
from PIL import Image, ImageEnhance
from pokemon.master import catch_em_all, get_pokemon

from helpers.utils import Embed, check_args, guess_string

channels = Dict()

DEFAULT_CONFIG = Dict({"pokemon": {"status": 0, "scoreboard": {}}})


def get_channel(channel_id):
    if channel_id not in channels.keys():
        channels[channel_id] = deepcopy(DEFAULT_CONFIG)

    return channels[channel_id]


class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pokemons = catch_em_all()
        self.session = bot.session

    @commands.command(usage="<start | stop | scoreboard>")
    async def pokemon(self, ctx, *, cmd):
        channel = get_channel(ctx.channel.id)

        if cmd == "start":
            channel.pokemon.status = 1
            while channel.pokemon.status != 0:
                await self._pokemon_start(ctx)
            await self._pokemon_show_scoreboard(ctx)
        elif cmd == "stop":
            channel.pokemon.status = 0
            await ctx.send(
                embed=Embed(description="Pokemon game will stop after this.")
            )
        elif cmd == "scoreboard":
            await self._pokemon_show_scoreboard(ctx)

    async def _pokemon_start(self, ctx):
        channel = get_channel(ctx.channel.id)

        name, original_img, black_img = await self._pokemon_get()

        print(name)

        embed = Embed()
        embed.set_author(
            name="Who's that pokemon?", icon_url="https://i.imgur.com/3sQh8aN.png"
        )
        embed.set_image(url="attachment://image.png")

        guess_embed = embed.copy()
        guess_embed.set_footer(text=guess_string(name))

        guess_msg = await ctx.send(
            embed=guess_embed, file=discord.File(black_img, "image.png")
        )

        winner_embed = embed.copy()
        someone_answered = False

        def check(m):
            nonlocal someone_answered

            if m.content:
                someone_answered = True
                if m.author.id not in channel.pokemon.scoreboard:
                    channel.pokemon.scoreboard[m.author.id] = 0

            return m.channel == ctx.channel and m.content.lower() == name.lower()

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            winner_embed.description = "**No one**"
            channel.pokemon.status = 0
        else:
            if msg.author.id not in channel.pokemon.scoreboard:
                channel.pokemon.scoreboard[msg.author.id] = 1
            else:
                channel.pokemon.scoreboard[msg.author.id] += 1
            winner_embed.description = f"**{msg.author.name}**"

        winner_embed.description += (
            f" got the correct answer!\nThe answer is **{name}**"
        )

        await guess_msg.delete()
        await ctx.send(embed=winner_embed, file=discord.File(original_img, "image.png"))

        if not someone_answered:
            await ctx.send(
                embed=Embed(
                    description="Pokemon game will stop because no one tried to answer it."
                )
            )

    async def _pokemon_get(self):
        pokemon = Dict(list(get_pokemon(pokemons=self.pokemons).values())[0])
        res = await self.session.get(
            f"https://gearoid.me/pokemon/images/artwork/{pokemon.id}.png"
        )

        original_img = BytesIO(await res.read())
        black_img = BytesIO()

        image = Image.open(deepcopy(original_img))
        enh = ImageEnhance.Brightness(image)
        enh.enhance(0).save(black_img, "PNG")
        black_img.seek(0)

        return (pokemon.name, original_img, black_img)

    async def _pokemon_show_scoreboard(self, ctx):
        scoreboard = get_channel(ctx.channel.id).pokemon.scoreboard

        scores = sorted(scoreboard.items(), key=lambda kv: kv[1], reversed=True)
        scores = map(lambda x: f"**{self.bot.get_user(x[0])}:** {x[1]}", scores)

        embed = Embed(title="Scoreboard", description="\n".join(scores))
        embed.set_author(
            name="Who's that pokemon?", icon_url="https://i.imgur.com/3sQh8aN.png"
        )

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Game(bot))
