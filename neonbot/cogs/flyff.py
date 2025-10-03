from typing import cast

import discord
from discord import app_commands
from discord.ext import commands
from durations_nlp import Duration

from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.classes.flyff import Flyff
from neonbot.models.flyff import FlyffTimer
from neonbot.models.guild import GuildModel


class FlyffCog(commands.Cog):
    flyff = app_commands.Group(
        name='flyff',
        description='Flyff commands',
        guild_ids=bot.owner_guilds,
        default_permissions=discord.Permissions(administrator=True),
    )

    @flyff.command(name='start')
    async def start(self, interaction: discord.Interaction) -> None:
        server = GuildModel.get_instance(interaction.guild.id)

        server.flyff.channel_id = interaction.channel_id
        await server.save_changes()

        Flyff.start_listener(interaction.guild.id)

        await cast(discord.InteractionResponse, interaction.response).send_message(
            embed=Embed(f'Started monitor on {interaction.channel.mention}'), ephemeral=True
        )

    @flyff.command(name='set_world_start')
    async def set_world_start(self, interaction: discord.Interaction, time: str) -> None:
        server = GuildModel.get_instance(interaction.guild.id)

        server.flyff.world_start_time = time
        await server.save_changes()

        await cast(discord.InteractionResponse, interaction.response).send_message(
            embed=Embed(f'Set world start to `{time}`'), ephemeral=True
        )

    @flyff.command(name='add_timer')
    async def add_timer(self, interaction: discord.Interaction, name: str, initial_interval: str,
                        interval: str) -> None:
        server = GuildModel.get_instance(interaction.guild.id)

        if name in server.flyff.timers:
            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed('Name already in timer list.'), ephemeral=True
            )
            return

        initial_interval = Duration(initial_interval).to_seconds()
        interval = Duration(interval).to_seconds()

        server.flyff.timers[name] = FlyffTimer(initial_interval=initial_interval, interval=interval)
        await server.save_changes()

        await cast(discord.InteractionResponse, interaction.response).send_message(
            embed=Embed(f'Added `{name}` timer'), ephemeral=True
        )

    @flyff.command(name='delete_timer')
    async def delete_timer(self, interaction: discord.Interaction, name: str) -> None:
        server = GuildModel.get_instance(interaction.guild.id)

        if name not in server.flyff.timers:
            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed('Name not in timer list.'), ephemeral=True
            )
            return

        del server.flyff.timers[name]
        await server.save_changes()

        await cast(discord.InteractionResponse, interaction.response).send_message(
            embed=Embed(f'Removed `{name}` timer on {interaction.channel.mention}'), ephemeral=True
        )


# noinspection PyShadowingNames
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FlyffCog())
