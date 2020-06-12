import logging
from typing import cast

import discord
from addict import Dict
from discord.ext import commands

from .. import bot
from ..classes import Connect4, Embed, Pokemon
from ..helpers.log import Log

log = cast(Log, logging.getLogger(__name__))


def get_channel(ctx: commands.Context) -> Dict:
    rooms = bot.game
    if ctx.channel.id not in rooms.keys():
        rooms[ctx.channel.id] = Dict(pokemon=Pokemon(ctx), connect4=Connect4(ctx))

    return rooms[ctx.channel.id]


class Game(commands.Cog):
    @commands.command(usage="<start | stop | scoreboard>")
    @commands.guild_only()
    async def pokemon(self, ctx: commands.Context, *, command: str) -> None:
        """Starts, stops, or shows the scoreboard of the pokemon game."""

        pokemon = get_channel(ctx).pokemon

        if command == "start":
            if pokemon.status == 1:
                return await ctx.send(
                    embed=Embed("Pokemon game already started."), delete_after=5
                )

            pokemon.status = 1
            while pokemon.status != 0:
                await pokemon.start()

            if pokemon.timed_out:
                return pokemon.__init__(ctx.channel)

            await pokemon.show_scoreboard()
        elif command == "stop":
            pokemon.status = 0
            await ctx.send(embed=Embed("Pokemon game will stop after this."))
        elif command == "scoreboard":
            await pokemon.show_scoreboard()

    @commands.command()
    @commands.guild_only()
    async def connect4(self, ctx: commands.Context) -> None:
        """Starts connect4 game and waits for the players if players are insufficient."""

        connect4 = get_channel(ctx).connect4
        if connect4.players == 2:
            await ctx.send(
                embed=Embed("Connect4 game is already running"), delete_after=5
            )
        else:
            await connect4.join(ctx.author)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Game())
