import contextlib
import sys
from io import StringIO
from typing import Generator, Optional

import discord
from discord import app_commands
from discord.ext import commands

from .. import bot
from ..classes.embed import Embed
from ..models.guild import Guild


@contextlib.contextmanager
def stdout_io() -> Generator[StringIO, None, None]:
    old = sys.stdout
    stdout = StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old


class Administration(commands.Cog):
    """Administration commands that handles the management of the bot"""

    server = app_commands.Group(name='settings', description="Configure the settings of the bot for this server.",
                                default_permissions=discord.Permissions.elevated())

    settings = app_commands.Group(name='bot', description="Configure the settings of the bot globally.",
                                  default_permissions=discord.Permissions.elevated(),
                                  guild_ids=[bot.base_guild_id])

    @commands.command()
    @commands.is_owner()
    async def eval(self, ctx: commands.Context, *, code: str) -> None:
        """Evaluates a line/s of python code. *BOT_OWNER"""

        guild_id = ctx.guild.id if ctx.guild else None

        variables = {
            "bot": bot,
            "ctx": ctx,
        }

        if code.startswith("```") and code.endswith("```"):
            code = "\n".join(code.splitlines()[1:-1])

        try:
            lines = "\n".join([f"  {i}" for i in code.splitlines()])

            with stdout_io() as s:
                exec(f"async def x():\n{lines}\n", variables)
                await eval("x()", variables)
            output = s.getvalue()
        except Exception as e:
            output = str(e)
            await ctx.message.add_reaction("❌")
        else:
            await ctx.message.add_reaction("👌")

        if output:
            msg_array = [output[i: i + 1900] for i in range(0, len(output), 1900)]

            messages = ["```py\n" + msg.strip("\n") + "```" for msg in msg_array]
            for message in messages:
                await ctx.send(message)

    @app_commands.command(name='prune')
    @app_commands.default_permissions(manage_messages=True)
    async def prune(
            self,
            interaction: discord.Interaction,
            count: app_commands.Range[int, 1, 1000],
            member: Optional[discord.Member] = None,
    ) -> None:
        """Deletes a number of messages of a specific member (if specified). *MANAGE_MESSAGES"""

        guild = Guild.get_instance(interaction.guild_id)

        await interaction.response.defer()

        async for message in interaction.channel.history(limit=1000 if member else count):
            if count <= 0:
                break

            if not member or message.author == member:
                await bot.delete_message(message)
                count -= 1

        await interaction.delete_original_response()

    @server.command(name='prefix')
    async def prefix(self, interaction: discord.Interaction, prefix: str) -> None:
        """Sets the prefix of the current server. *ADMINISTRATOR"""

        guild = Guild.get_instance(interaction.guild_id)
        await guild.update({'prefix': prefix})

        await interaction.response.send_message(embed=Embed(f"Prefix is now set to `{guild.get('prefix')}`."))

    @server.command(name='deleteoncmd')
    async def deleteoncmd(self, interaction: discord.Interaction) -> None:
        """Enables/Disables the deletion of message after execution. *BOT_OWNER"""

        guild = Guild.get_instance(interaction.guild_id)
        await guild.update({'deleteoncmd': not guild.get('deleteoncmd')})

        await interaction.response.send_message(
            embed=Embed(
                f"Delete on command is now set to {'enabled' if guild.get('deleteoncmd') else 'disabled'}."
            )
        )

    @settings.command(name='setstatus')
    async def setstatus(self, interaction: discord.Interaction, status: discord.Status) -> None:
        """Sets the status of the bot. *BOT_OWNER"""

        if status is False:
            return

        await bot.settings.update({'status': status})

        await bot.change_presence(status=discord.Status[bot.settings.get('status')])
        await interaction.response.send_message(embed=Embed(f"Status is now set to {bot.settings.get('status')}."))

    @settings.command(name='setpresence')
    async def setpresence(
            self,
            interaction: discord.Interaction,
            presence_type: discord.ActivityType,
            name: str,
    ) -> None:
        """Sets the presence of the bot. *BOT_OWNER"""

        if presence_type is False:
            return

        bot.settings.set('game', {
            'type': presence_type,
            'name': name
        })
        await bot.settings.save()

        await bot.change_presence(
            activity=discord.Activity(
                name=name, type=discord.ActivityType[bot.settings.get('game.type')]
            )
        )
        await interaction.response.send_message(
            embed=Embed(
                f"Presence is now set to {bot.settings.get('game.type')} {bot.settings.get('game.name')}."
            )
        )


# noinspection PyShadowingNames
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Administration())
