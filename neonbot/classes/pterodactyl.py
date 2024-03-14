import asyncio
from datetime import datetime

import discord
import validators
from discord.utils import find
from envparse import env

from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.models.guild import Guild
from neonbot.utils.constants import ICONS
from neonbot.utils.functions import format_uptime


class Pterodactyl:
    URL = env.str('PTERODACTYL_URL')
    API_KEY = env.str('PTERODACTYL_API_KEY')

    def __init__(self, server_id: str):
        self.server_id = server_id

    async def get_server_details(self):
        res = await bot.session.get(
            self.URL + '/api/client/servers/' + self.server_id,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.API_KEY}"
            }
        )
        return await res.json() if res.status == 200 else False

    async def get_server_resources(self):
        res = await bot.session.get(
            self.URL + '/api/client/servers/' + self.server_id + '/resources',
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.API_KEY}"
            }
        )
        return await res.json() if res.status == 200 else False

    @staticmethod
    async def start_monitor(channel_id, server_id):
        ptero = Pterodactyl(server_id)

        details, resources = await asyncio.gather(
            ptero.get_server_details(),
            ptero.get_server_resources()
        )

        uuid = details['attributes']['uuid']
        name = details['attributes']['name']
        node = details['attributes']['node']

        try:
            state = resources['attributes']['current_state']
        except KeyError:
            state = 'offline'

        embed = Embed(timestamp=datetime.now())
        embed.set_author(name, url=Pterodactyl.URL + '/server/' + server_id)
        embed.set_description(node)
        embed.set_thumbnail(ICONS['green'] if state == 'running' else ICONS['red'])
        embed.set_footer(uuid)

        if state != 'offline':
            state = resources['attributes']['current_state']

            try:
                image_url = find(
                    lambda data: data['attributes']['name'] == 'DISCORD_IMAGE_URL',
                    details['attributes']['relationships']['variables']['data']
                )['attributes']['server_value']
            except KeyError:
                image_url = None

            current_cpu_usage = resources['attributes']['resources']['cpu_absolute']
            current_cpu_usage = f"{current_cpu_usage:.2f}"
            max_cpu_usage = details['attributes']['limits']['cpu']
            max_cpu_usage = f'{max_cpu_usage}' if max_cpu_usage != 0 else '∞'

            current_memory_usage = resources['attributes']['resources']['memory_bytes'] / 1024 / 1024
            current_memory_usage = f"{current_memory_usage:,.0f}"
            max_memory_usage = details['attributes']['limits']['memory']
            max_memory_usage = f'{max_memory_usage:,.0f}' if max_memory_usage != 0 else '∞'

            uptime = resources['attributes']['resources']['uptime']

            if image_url and validators.url(image_url):
                embed.set_image(image_url)

            embed.add_field('Status', state.title())
            embed.add_field('Uptime', format_uptime(uptime))
            embed.add_field('\u200b', '\u200b')
            embed.add_field('CPU Usage', f"{current_cpu_usage} / {max_cpu_usage} %")
            embed.add_field('Memory Usage', f"{current_memory_usage} / {max_memory_usage} MB")
            embed.add_field('\u200b', '\u200b')
        else:
            embed.add_field('Status', state.title())

        channel = bot.get_channel(channel_id)
        server = Guild.get_instance(channel.guild.id)

        message_id = server.ptero.servers[server_id].message_id

        try:
            message = await channel.fetch_message(message_id) if message_id else None
        except discord.NotFound:
            message = None

        if not message:
            message = await channel.send(embed=embed)
            server.ptero.servers[server_id].message_id = message.id
            await server.save_changes()
        else:
            return await message.edit(embed=embed)
