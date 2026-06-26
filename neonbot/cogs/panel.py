from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from i18n import t

from neonbot.classes.discord_utils.embed import Embed
from neonbot.classes.panel import Panel
from neonbot.env import OWNER_GUILD_IDS
from neonbot.models.guild import GuildModel
from neonbot.models.panel import PanelServer

if TYPE_CHECKING:
    from neonbot import NeonBot


class PanelCog(commands.Cog):
    panel = app_commands.Group(
        name='panel',
        description='Panel commands',
        guild_ids=OWNER_GUILD_IDS,
        default_permissions=discord.Permissions(administrator=True),
    )

    @panel.command(name='startmonitor')
    async def startmonitor(self, interaction: discord.Interaction['NeonBot'], server_id: str) -> None:
        server = GuildModel.get_instance(interaction.guild.id)

        details = await Panel(interaction.client, server_id).get_server_details()

        if not details:
            await interaction.response.send_message(
                embed=Embed(t('panel.invalid_server_id')), ephemeral=True
            )
            return

        if server_id in server.panel.servers:
            await interaction.response.send_message(
                embed=Embed(t('panel.server_id_exists')), ephemeral=True
            )
            return

        server.panel.servers[server_id] = PanelServer(channel_id=interaction.channel_id)
        await server.save_changes(False)

        Panel.start_listener(interaction.client, interaction.guild.id)

        await interaction.response.send_message(
            embed=Embed(t('panel.monitor_started', server_id=server_id, channel=interaction.channel.mention)), ephemeral=True
        )

    @panel.command(name='deletemonitor')
    async def deletemonitor(self, interaction: discord.Interaction['NeonBot'], server_id: str) -> None:
        server = GuildModel.get_instance(interaction.guild.id)

        if server_id not in server.panel.servers:
            await interaction.response.send_message(
                embed=Embed(t('panel.server_id_not_found')), ephemeral=True
            )
            return

        panel = server.panel.servers[server_id]

        if panel.channel_id and panel.message_id:
            channel = interaction.client.get_channel(panel.channel_id)
            if channel:
                try:
                    message = await channel.fetch_message(panel.message_id)
                    await interaction.client.delete_message(message)
                except discord.NotFound:
                    pass

        server.panel.servers[server_id] = PanelServer()
        await server.save_changes(False)

        await interaction.response.send_message(
            embed=Embed(t('panel.monitor_removed', server_id=server_id, channel=interaction.channel.mention)), ephemeral=True
        )

    @startmonitor.autocomplete('server_id')
    async def startmonitor_autocomplete(self, interaction: discord.Interaction['NeonBot'], current: str):
        panel = GuildModel.get_instance(interaction.guild.id).panel
        servers = [
            {'id': server['attributes']['identifier'], 'name': server['attributes']['name']}
            for server in (await Panel(interaction.client).get_server_list())['data']
        ]

        return [
            app_commands.Choice(name=server['name'], value=server['id'])
            for server in servers
            if server['id'] not in panel.servers and ((current and current in server['name']) or not current)
        ]

    @deletemonitor.autocomplete('server_id')
    async def deletemonitor_autocomplete(self, interaction: discord.Interaction['NeonBot'], current: str):
        panel = GuildModel.get_instance(interaction.guild.id).panel
        servers = [
            {'id': server['attributes']['identifier'], 'name': server['attributes']['name']}
            for server in (await Panel(interaction.client).get_server_list())['data']
        ]

        return [
            app_commands.Choice(name=server['name'], value=server['id'])
            for server in servers
            if server['id'] in panel.servers and ((current and current in server['name']) or not current)
        ]


async def setup(bot: 'NeonBot') -> None:
    await bot.add_cog(PanelCog())
