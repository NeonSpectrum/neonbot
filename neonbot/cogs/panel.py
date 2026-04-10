from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

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
                embed=Embed('Invalid server id.'), ephemeral=True
            )
            return

        if server_id in server.panel.servers:
            await interaction.response.send_message(
                embed=Embed('Server id already exists.'), ephemeral=True
            )
            return

        server.panel.servers[server_id] = PanelServer(channel_id=interaction.channel_id)
        await server.save_changes(False)

        Panel.start_listener(interaction.client, interaction.guild.id)

        await interaction.response.send_message(
            embed=Embed(f'Started monitor for `{server_id}` on {interaction.channel.mention}'), ephemeral=True
        )

    @panel.command(name='deletemonitor')
    async def deletemonitor(self, interaction: discord.Interaction['NeonBot'], server_id: str) -> None:
        server = GuildModel.get_instance(interaction.guild.id)

        if server_id not in server.panel.servers:
            await interaction.response.send_message(
                embed=Embed('Server id not in monitor list.'), ephemeral=True
            )
            return

        panel = server.panel.servers[server_id]

        if panel.channel_id and panel.message_id:
            await interaction.client.delete_message(await interaction.client.get_channel(panel.channel_id).fetch_message(panel.message_id))

        server.panel.servers[server_id] = PanelServer()
        await server.save_changes(False)

        await interaction.response.send_message(
            embed=Embed(f'Removed monitor for `{server_id}` on {interaction.channel.mention}'), ephemeral=True
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
