from addict import Dict
from discord.ext import commands

from ..classes import Connect4, Pokemon
from ..helpers.utils import Embed

rooms = Dict()


def get_channel(channel_id):
    if channel_id not in rooms.keys():
        rooms[channel_id] = Dict(
            {"pokemon": Pokemon(channel_id), "connect4": Connect4(channel_id)}
        )

    return rooms[channel_id]


class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(usage="<start | stop | scoreboard>")
    async def pokemon(self, ctx, *, cmd):
        pokemon = get_channel(ctx.channel.id).pokemon

        if cmd == "start":
            if pokemon.status == 1:
                return await ctx.send(
                    embed=Embed("Pokemon game already started."), delete_after=5
                )

            pokemon.status = 1
            while pokemon.status != 0:
                await pokemon.start()

            if pokemon.timed_out:
                return pokemon.__init__(ctx.channel.id)

            await pokemon.show_scoreboard()
        elif cmd == "stop":
            pokemon.status = 0
            await ctx.send(embed=Embed("Pokemon game will stop after this."))
        elif cmd == "scoreboard":
            await pokemon.show_scoreboard()

    @commands.command()
    async def connect4(self, ctx):
        connect4 = get_channel(ctx.channel.id).connect4
        if connect4.players == 2:
            await ctx.send(
                embed=Embed("Connect4 game is already running"), delete_after=5
            )
        else:
            await connect4.join(ctx.author)


def setup(bot):
    bot.add_cog(Game(bot))
