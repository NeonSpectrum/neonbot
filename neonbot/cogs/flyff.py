import os
import random
from datetime import datetime
from time import time
from typing import Union, cast

import discord
import psutil
from discord import app_commands
from discord.ext import commands
from discord.utils import format_dt
from envparse import env
from yt_dlp import version as ytdl_version

from neonbot import __author__, __title__, __version__, bot
from neonbot.classes.embed import Embed
from neonbot.classes.gemini import GeminiChat
from neonbot.utils.constants import ICONS
from neonbot.utils.functions import format_seconds, generate_profile_member_embed, generate_profile_user_embed


class Flyff(commands.Cog):
    flyff = app_commands.Group(
        name='flyff',
        description='Flyff commands',
        guild_ids=bot.owner_guilds,
        default_permissions=discord.Permissions(administrator=True),
    )

    @panel.command(name='startmonitor')
    async def startmonitor(self, interaction: discord.Interaction, server_id: str) -> None:
        server = GuildModel.get_instance(interaction.guild.id)

        details = await Panel(server_id).get_server_details()

        if not details:
            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed('Invalid server id.'), ephemeral=True
            )
            return

        if server_id in server.panel.servers:
            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed('Server id already exists.'), ephemeral=True
            )
            return

        server.panel.servers[server_id] = PanelServer(channel_id=interaction.channel_id)
        await server.save_changes()

        Panel.start_listener(interaction.guild.id)

        await cast(discord.InteractionResponse, interaction.response).send_message(
            embed=Embed(f'Started monitor for `{server_id}` on {interaction.channel.mention}'), ephemeral=True
        )

    @panel.command(name='delete_timer')
    async def delete_timer(self, interaction: discord.Interaction, name: str) -> None:
        server = GuildModel.get_instance(interaction.guild.id)

        if name not in server.flyff.timers:
            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed('Name not in timer list.'), ephemeral=True
            )
            return

        timers = server.flyff.timers
        server.flyff.timers[name] = FlyffTimer()
        await server.save_changes()

        await cast(discord.InteractionResponse, interaction.response).send_message(
            embed=Embed(f'Removed monitor for `{server_id}` on {interaction.channel.mention}'), ephemeral=True
        )

    @startmonitor.autocomplete('server_id')
    async def startmonitor_autocomplete(self, interaction: discord.Interaction, current: str):
        panel = GuildModel.get_instance(interaction.guild.id).panel
        servers = [
            {'id': server['attributes']['identifier'], 'name': server['attributes']['name']}
            for server in (await Panel.get_server_list())['data']
        ]

        return [
            app_commands.Choice(name=server['name'], value=server['id'])
            for server in servers
            if server['id'] not in panel.servers and ((current and current in server['name']) or not current)
        ]

    @deletemonitor.autocomplete('server_id')
    async def deletemonitor_autocomplete(self, interaction: discord.Interaction, current: str):
        panel = GuildModel.get_instance(interaction.guild.id).panel
        servers = [
            {'id': server['attributes']['identifier'], 'name': server['attributes']['name']}
            for server in (await Panel.get_server_list())['data']
        ]

        return [
            app_commands.Choice(name=server['name'], value=server['id'])
            for server in servers
            if server['id'] in panel.servers and ((current and current in server['name']) or not current)
        ]


# noinspection PyShadowingNames
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility())
