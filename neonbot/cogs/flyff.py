from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from durations_nlp import Duration

from neonbot.classes.discord_utils.embed import Embed
from neonbot.classes.flyff import Flyff
from neonbot.models.flyff import FlyffAlertChannel, FlyffModel, FlyffPingChannel, FlyffTimer, FlyffWebhookChannel

if TYPE_CHECKING:
    from neonbot import NeonBot


class FlyffCog(commands.Cog):
    flyff = app_commands.Group(
        name='flyff',
        description='Flyff commands',
        default_permissions=discord.Permissions(administrator=True),
    )

    def __init__(self, bot: 'NeonBot'):
        self.bot = bot

    @flyff.command(name='start')
    @app_commands.choices(
        option=[
            app_commands.Choice(name='Status', value='status'),
            app_commands.Choice(name='Alert', value='alert'),
            app_commands.Choice(name='Ping', value='ping'),
        ]
    )
    async def start(self, interaction: discord.Interaction['NeonBot'], option: str) -> None:
        if not self.bot.flyff_settings.world_start_time:
            await interaction.response.send_message(
                embed=Embed('Set world start time first.'), ephemeral=True
            )
            return

        if option == 'status':
            self.bot.flyff_settings.status_channels[interaction.channel_id] = 0
        elif option == 'alert':
            self.bot.flyff_settings.alert_channels.append(FlyffAlertChannel(channel_id=interaction.channel_id))
        elif option == 'ping':
            self.bot.flyff_settings.ping_channels.append(FlyffPingChannel(channel_id=interaction.channel_id))

        await self.bot.flyff_settings.save_changes(False)

        flyff = Flyff(self.bot)
        await flyff.refresh_status()

        await interaction.response.send_message(
            embed=Embed(f'Started monitor on {interaction.channel.mention}'), ephemeral=True
        )

    @flyff.command(name='set_world_start')
    async def set_world_start(self, interaction: discord.Interaction['NeonBot'], time: str) -> None:
        self.bot.flyff_settings = await FlyffModel.get_instance()

        self.bot.flyff_settings.world_start_time = time
        await self.bot.flyff_settings.save_changes(False)

        flyff = Flyff(self.bot)
        await flyff.refresh_status()

        await interaction.response.send_message(
            embed=Embed(f'Set world start to `{time}`'), ephemeral=True
        )

    @flyff.command(name='add_timer')
    async def add_timer(
        self, interaction: discord.Interaction['NeonBot'], name: str, initial_interval: str, interval: str
    ) -> None:
        self.bot.flyff_settings = await FlyffModel.get_instance()

        if name in self.bot.flyff_settings.timers:
            await interaction.response.send_message(
                embed=Embed('Name already in timer list.'), ephemeral=True
            )
            return

        initial_interval = Duration(initial_interval).to_seconds()
        interval = Duration(interval).to_seconds()

        self.bot.flyff_settings.timers[name] = FlyffTimer(initial_interval=initial_interval, interval=interval)
        await self.bot.flyff_settings.save_changes(False)

        await interaction.response.send_message(
            embed=Embed(f'Added `{name}` timer'), ephemeral=True
        )

    @flyff.command(name='delete_timer')
    async def delete_timer(self, interaction: discord.Interaction['NeonBot'], name: str) -> None:
        self.bot.flyff_settings = await FlyffModel.get_instance()

        if name not in self.bot.flyff_settings.timers:
            await interaction.response.send_message(
                embed=Embed('Name not in timer list.'), ephemeral=True
            )
            return

        del self.bot.flyff_settings.timers[name]
        await self.bot.flyff_settings.save_changes(False)

        await interaction.response.send_message(
            embed=Embed(f'Removed `{name}` timer on {interaction.channel.mention}'), ephemeral=True
        )

    @flyff.command(name='add_fixed_timer')
    async def add_fixed_timer(self, interaction: discord.Interaction['NeonBot'], name: str, start_time: str) -> None:
        self.bot.flyff_settings = await FlyffModel.get_instance()

        if name in self.bot.flyff_settings.fixed_timers:
            await interaction.response.send_message(
                embed=Embed('Name already in fixed timer list.'), ephemeral=True
            )
            return

        self.bot.flyff_settings.fixed_timers[name] = start_time.split(',')
        await self.bot.flyff_settings.save_changes(False)

        await interaction.response.send_message(
            embed=Embed(f'Added `{name}` fixed timer'), ephemeral=True
        )

    @flyff.command(name='delete_fixed_timer')
    async def delete_fixed_timer(self, interaction: discord.Interaction['NeonBot'], name: str) -> None:
        self.bot.flyff_settings = await FlyffModel.get_instance()

        if name not in self.bot.flyff_settings.fixed_timers:
            await interaction.response.send_message(
                embed=Embed('Name not in fixed timer list.'), ephemeral=True
            )
            return

        del self.bot.flyff_settings.fixed_timers[name]
        await self.bot.flyff_settings.save_changes(False)

        await interaction.response.send_message(
            embed=Embed(f'Removed `{name}` fixed timer on {interaction.channel.mention}'), ephemeral=True
        )

    @flyff.command(name='add_webhook_tts')
    async def add_webhook_tts(self, interaction: discord.Interaction['NeonBot'], name: str, url: str) -> None:
        self.bot.flyff_settings = await FlyffModel.get_instance()

        if name in self.bot.flyff_settings.webhooks:
            await interaction.response.send_message(
                embed=Embed('Webhook name already in the list.'), ephemeral=True
            )
            return

        self.bot.flyff_settings.webhooks[name] = url
        await self.bot.flyff_settings.save_changes(False)

        await interaction.response.send_message(
            embed=Embed(f'Added `{name}` fixed timer'), ephemeral=True
        )

    @flyff.command(name='delete_webhook_tts')
    async def delete_webhook_tts(self, interaction: discord.Interaction['NeonBot'], name: str) -> None:
        self.bot.flyff_settings = await FlyffModel.get_instance()

        if name not in self.bot.flyff_settings.webhooks:
            await interaction.response.send_message(
                embed=Embed('Webhook name is not in list.'), ephemeral=True
            )
            return

        del self.bot.flyff_settings.webhooks[name]
        await self.bot.flyff_settings.save_changes(False)

        await interaction.response.send_message(
            embed=Embed(f'Removed `{name}` webhook'), ephemeral=True
        )

    @flyff.command(name='add_webhook')
    async def add_webhook(self, interaction: discord.Interaction['NeonBot'], url: str) -> None:
        self.bot.flyff_settings = await FlyffModel.get_instance()
        self.bot.flyff_settings.webhook_channels.append(FlyffWebhookChannel(url=url))
        await self.bot.flyff_settings.save_changes(False)

        await interaction.response.send_message(
            embed=Embed(f'Added `{url}` webhook url'), ephemeral=True
        )


async def setup(bot: 'NeonBot') -> None:
    await bot.add_cog(FlyffCog(bot))
