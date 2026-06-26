from typing import TYPE_CHECKING

from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands._types import Check
from i18n import t

from neonbot.discord_ui.embed import Embed
from neonbot.env import OWNER_IDS
from neonbot.utils.functions import ensure_ctx

if TYPE_CHECKING:
    from neonbot import NeonBot
    from neonbot.music.player import Player


def in_voice(app: bool = False) -> Check[Context['NeonBot']]:
    async def predicate(ctx: commands.Context['NeonBot']):
        if await ctx.bot.is_owner(ctx.author) and ctx.command.name == 'reset':
            return True

        if not ctx.author.voice:
            await ctx.reply(
                embed=Embed(t('event.in_voice_required')), ephemeral=True
            )
            return False
        return True

    return check(predicate, app)


def has_permission(app: bool = False) -> Check[Context['NeonBot']]:
    async def predicate(ctx: commands.Context['NeonBot']):
        ctx = await ensure_ctx(ctx)

        if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.reply(
                embed=Embed(t('event.no_send_permission')), ephemeral=True
            )
            return False

        if ctx.author.voice and not ctx.author.voice.channel.permissions_for(ctx.guild.me).connect:
            await ctx.reply(
                embed=Embed(t('event.no_connect_permission')), ephemeral=True
            )
            return False

        return True

    return check(predicate, app)


def has_player(app: bool = False) -> Check[Context['NeonBot']]:
    async def predicate(ctx: commands.Context['NeonBot']):
        ctx = await ensure_ctx(ctx)

        player: Player = ctx.bot.get_player_instance(ctx.guild.id)

        if not player or not player.ctx or len(player.playlist) == 0:
            await ctx.reply(embed=Embed(t('event.no_active_player')), ephemeral=True)
            return False
        return True

    return check(predicate, app)


def is_owner(app: bool = False) -> Check[Context['NeonBot']]:
    async def predicate(ctx: commands.Context['NeonBot']):
        ctx = await ensure_ctx(ctx)

        if (ctx.guild and ctx.guild.id not in ctx.bot.owner_guilds) or (not ctx.guild and ctx.author.id not in OWNER_IDS):
            await ctx.reply(
                embed=Embed(t('event.no_command_permission')), ephemeral=True
            )
            return False

        return True

    return check(predicate, app)


def check(predicate: Check[Context['NeonBot']], app: bool):
    if app:
        return app_commands.check(predicate)

    return commands.check(predicate)
