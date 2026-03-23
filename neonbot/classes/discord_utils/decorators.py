from typing import TYPE_CHECKING

from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands._types import Check

from neonbot.classes.discord_utils.embed import Embed
from neonbot.env import OWNER_IDS
from neonbot.utils.functions import ensure_ctx

if TYPE_CHECKING:
    from neonbot import NeonBot
    from neonbot.classes.player.player import Player


def in_voice(app: bool = False) -> Check[Context['NeonBot']]:
    async def predicate(ctx: commands.Context['NeonBot']):
        if await ctx.bot.is_owner(ctx.author) and ctx.command.name == 'reset':
            return True

        if not ctx.author.voice:
            await ctx.reply(
                embed=Embed('You need to be in the channel.'), ephemeral=True
            )
            return False
        return True

    return check(predicate, app)


def has_permission(app: bool = False) -> Check[Context['NeonBot']]:
    async def predicate(ctx: commands.Context['NeonBot']):
        ctx = await ensure_ctx(ctx)

        if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.reply(
                embed=Embed("I don't have permission to send message on this channel."), ephemeral=True
            )
            return False

        if ctx.author.voice and not ctx.author.voice.channel.permissions_for(ctx.guild.me).connect:
            await ctx.reply(
                embed=Embed("I don't have permission to connect to that voice channel."), ephemeral=True
            )
            return False

        return True

    return check(predicate, app)


def has_player(app: bool = False) -> Check[Context['NeonBot']]:
    async def predicate(ctx: commands.Context['NeonBot']):
        ctx = await ensure_ctx(ctx)

        player: Player = ctx.bot.lavalink.player_manager.get(ctx.guild.id)

        if not player:
            await ctx.reply(embed=Embed('No active player.'), ephemeral=True)
            return False
        return True

    return check(predicate, app)


def is_owner(app: bool = False) -> Check[Context['NeonBot']]:
    async def predicate(ctx: commands.Context['NeonBot']):
        ctx = await ensure_ctx(ctx)

        if (ctx.guild and ctx.guild.id not in ctx.bot.owner_guilds) or (not ctx.guild and ctx.author.id not in OWNER_IDS):
            await ctx.reply(
                embed=Embed("You do not have permission to use this command."), ephemeral=True
            )
            return False

        return True

    return check(predicate, app)


def check(predicate: Check[Context['NeonBot']], app: bool):
    if app:
        return app_commands.check(predicate)

    return commands.check(predicate)
