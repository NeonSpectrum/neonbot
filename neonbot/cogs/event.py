import traceback

import discord
from discord.app_commands import AppCommandError
from discord.ext import commands

from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.classes.player import Player
from neonbot.models.guild import Guild
from neonbot.utils import log, exceptions
from neonbot.utils.functions import get_command_string


class Event(commands.Cog):
    @staticmethod
    @bot.event
    async def on_connect() -> None:
        await bot.fetch_app_info()
        log.info(f"Logged in as {bot.user}")

    @staticmethod
    @bot.event
    async def on_disconnect() -> None:
        # log.warn("Disconnected!")
        pass

    @staticmethod
    @bot.event
    async def on_ready() -> None:
        await bot.db.get_guilds(bot.guilds)
        log.info("Ready!\n")
        bot.set_ready()

    @staticmethod
    @bot.event
    async def on_message(message: discord.Message) -> None:
        if not bot.is_ready() or message.author.id == bot.user.id:
            return

        ctx = await bot.get_context(message)

        if str(ctx.channel.type) == "private":
            if message.content.lower() == "invite":
                return await bot.send_invite_link(message)

            log.info(f"DM from {ctx.author}: {message.content}")
            await bot.send_to_owner(
                embed=Embed(title=f"DM from {ctx.author}", description=message.content),
                sender=ctx.author.id,
            )
            return

        if ctx.command is not None:
            async with ctx.channel.typing():
                await bot.process_commands(message)

    @staticmethod
    @bot.event
    async def on_interaction(interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.application_command:
            return

        log.cmd(interaction, get_command_string(interaction), guild=interaction.guild or "N/A")

    @staticmethod
    @bot.event
    async def on_app_command_error(interaction: discord.Interaction, error: AppCommandError) -> None:
        error = getattr(error, "original", error)
        ignored = discord.NotFound, commands.BadArgument, commands.CheckFailure
        send_msg = exceptions.YtdlError, discord.app_commands.AppCommandError, discord.app_commands.CommandInvokeError

        tb = traceback.format_exception(
            error, value=error, tb=error.__traceback__
        )

        tb_msg = "\n".join(tb)[:1000] + "..."

        if type(error) in ignored:
            return

        log.cmd(interaction, f"Command error: {error}")

        if isinstance(error, send_msg):
            await interaction.response.send_message(embed=Embed(error))
            return

        embed = Embed("There was an error executing the command. Please contact the administrator.")

        await bot.send_response(interaction, embed=embed)

        embed = Embed(
            title="Traceback Exception",
            description=f"Command: ```{get_command_string(interaction)}``````py\n{tb_msg}```",
        )

        await bot.send_to_owner(embed=embed)

        raise error

    @staticmethod
    @bot.event
    async def on_guild_join(guild):
        log.info(f"Creating database for {guild}...")
        await Guild.get_instance(guild.id).create_default_collection()

    @staticmethod
    @bot.event
    async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            if member.id != bot.user.id:
                return

            player = Player.get_instance_from_guild(member.guild)
            player.reset()


# noinspection PyShadowingNames
async def setup(bot: commands.Bot) -> None:
    bot.tree.on_error = Event.on_app_command_error
    await bot.add_cog(Event())
