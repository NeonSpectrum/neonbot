from typing import cast

import discord
from discord import app_commands
from discord.ext import commands
from durations_nlp import Duration

from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.classes.flyff import Flyff
from neonbot.models.flyff import FlyffTimer, FlyffModel, FlyffAlertChannel


class FlyffCog(commands.Cog):
    flyff = app_commands.Group(
        name='flyff',
        description='Flyff commands',
        default_permissions=discord.Permissions(administrator=True),
    )

    @flyff.command(name='start')
    @app_commands.choices(option=[
        app_commands.Choice(name="Status", value="status"),
        app_commands.Choice(name="Alert", value="alert"),
    ])
    async def start(self, interaction: discord.Interaction, option: str) -> None:
        if not bot.flyff_settings.world_start_time:
            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed('Set world start time first.'), ephemeral=True
            )
            return

        if option == 'status':
            bot.flyff_settings.status_channels[interaction.channel_id] = 0
        elif option == 'alert':
            bot.flyff_settings.alert_channels.append(FlyffAlertChannel(channel_id=interaction.channel_id))

        await bot.flyff_settings.save_changes()

        flyff = Flyff()
        await flyff.refresh_status()

        await cast(discord.InteractionResponse, interaction.response).send_message(
            embed=Embed(f'Started monitor on {interaction.channel.mention}'), ephemeral=True
        )

    @flyff.command(name='set_world_start')
    async def set_world_start(self, interaction: discord.Interaction, time: str) -> None:
        bot.flyff_settings = await FlyffModel.get_instance()

        bot.flyff_settings.world_start_time = time
        await bot.flyff_settings.save_changes()

        await cast(discord.InteractionResponse, interaction.response).send_message(
            embed=Embed(f'Set world start to `{time}`'), ephemeral=True
        )

    @flyff.command(name='add_timer')
    async def add_timer(self, interaction: discord.Interaction, name: str, initial_interval: str,
                        interval: str) -> None:
        bot.flyff_settings = await FlyffModel.get_instance()

        if name in bot.flyff_settings.timers:
            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed('Name already in timer list.'), ephemeral=True
            )
            return

        initial_interval = Duration(initial_interval).to_seconds()
        interval = Duration(interval).to_seconds()

        bot.flyff_settings.timers[name] = FlyffTimer(initial_interval=initial_interval, interval=interval)
        await bot.flyff_settings.save_changes()

        await cast(discord.InteractionResponse, interaction.response).send_message(
            embed=Embed(f'Added `{name}` timer'), ephemeral=True
        )

    @flyff.command(name='delete_timer')
    async def delete_timer(self, interaction: discord.Interaction, name: str) -> None:
        bot.flyff_settings = await FlyffModel.get_instance()

        if name not in bot.flyff_settings.timers:
            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed('Name not in timer list.'), ephemeral=True
            )
            return

        del bot.flyff_settings.timers[name]
        await bot.flyff_settings.save_changes()

        await cast(discord.InteractionResponse, interaction.response).send_message(
            embed=Embed(f'Removed `{name}` timer on {interaction.channel.mention}'), ephemeral=True
        )


# noinspection PyShadowingNames
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FlyffCog())
