import asyncio
import math
import random
from copy import deepcopy
from io import BytesIO

import discord
from addict import Dict
from PIL import Image, ImageEnhance
from pokemon.master import catch_em_all, get_pokemon

from .. import bot
from ..helpers.utils import Embed

pokemons = catch_em_all()


class Pokemon:
    def __init__(self, channel: discord.TextChannel):
        self.channel = bot.get_channel(channel.id)
        self.status = 0
        self.scoreboard = Dict()
        self.timed_out = False

    async def start(self):
        channel = self.channel

        name, original_img, black_img = await self.get()

        print(name)

        embed = Embed()
        embed.set_author(
            name="Who's that pokemon?", icon_url="https://i.imgur.com/3sQh8aN.png"
        )
        embed.set_image(url="attachment://image.png")

        guess_embed = embed.copy()
        guess_embed.set_footer(text=self.guess_string(name))

        guess_msg = await self.channel.send(
            embed=guess_embed, file=discord.File(black_img, "image.png")
        )

        winner_embed = embed.copy()
        someone_answered = False

        def check(m):
            nonlocal someone_answered

            if m.content:
                someone_answered = True
                if m.author.id not in self.scoreboard:
                    self.scoreboard[m.author.id] = 0

            return m.channel == channel and m.content.lower() == name.lower()

        try:
            msg = await bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            winner_embed.description = "**No one**"
            if not someone_answered:
                self.timed_out = True
                self.status = 0
        else:
            if msg.author.id not in self.scoreboard:
                self.scoreboard[msg.author.id] = 1
            else:
                self.scoreboard[msg.author.id] += 1
            winner_embed.description = f"**{msg.author.name}**"

        winner_embed.description += (
            f" got the correct answer!\nThe answer is **{name}**"
        )

        await guess_msg.delete()
        await channel.send(
            embed=winner_embed, file=discord.File(original_img, "image.png")
        )

        if not someone_answered:
            await channel.send(
                embed=Embed("Pokemon game paused because no one tried to answer it.")
            )

    async def get(self):
        pokemon = Dict(list(get_pokemon(pokemons=pokemons).values())[0])
        res = await bot.session.get(
            f"https://gearoid.me/pokemon/images/artwork/{pokemon.id}.png"
        )

        original_img = BytesIO(await res.read())
        black_img = BytesIO()

        image = Image.open(deepcopy(original_img))
        enh = ImageEnhance.Brightness(image)
        enh.enhance(0).save(black_img, "PNG")
        black_img.seek(0)

        return (pokemon.name, original_img, black_img)

    async def show_scoreboard(self):
        scoreboard = self.scoreboard

        scores = sorted(scoreboard.items(), key=lambda kv: kv[1], reverse=True)
        scores = list(map(lambda x: f"**{bot.get_user(x[0])}: {x[1]}**", scores))
        scores[0] += " `WINNER`"

        embed = Embed(title="Scoreboard", description="\n".join(scores))
        embed.set_author(
            name="Who's that pokemon?", icon_url="https://i.imgur.com/3sQh8aN.png"
        )

        await self.channel.send(embed=embed)

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
