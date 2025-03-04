import asyncio
from datetime import datetime, timedelta
from typing import List

import discord
import validators
from aiohttp import ClientSession, ContentTypeError
from discord.utils import find
from envparse import env

from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.models.guild import Guild
from neonbot.models.panel import PanelServer, Panel
from neonbot.utils import log
from neonbot.utils.constants import ICONS
from neonbot.utils.exceptions import ApiError
from neonbot.utils.functions import format_uptime


class Panel:
    URL = env.str('PANEL_URL')
    API_KEY = env.str('PANEL_API_KEY')
    MCSTATUS_API = 'https://api.mcstatus.io/v2/status/java'

    def __init__(self, server_id: str):
        self.server_id = server_id
        self.servers = None
        self.details = None
        self.resources = None
        self.session = ClientSession(ssl=False)

    async def get_server_details(self):
        res = await self.session.get(
            self.URL + '/api/client/servers/' + self.server_id,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.API_KEY}"
            },
        )

        if res.status != 200:
            raise ApiError(f'[{self.server_id}] Failed to fetch server details: {res.status}')

        self.details = await res.json()

        return self.details

    async def get_server_resources(self):
        res = await self.session.get(
            self.URL + '/api/client/servers/' + self.server_id + '/resources',
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.API_KEY}"
            }
        )

        if res.status != 200:
            raise ApiError(f'[{self.server_id}] Failed to fetch server resources: {res.status}')

        self.resources = await res.json()

        return self.resources

    @staticmethod
    async def get_server_list():
        res = await self.session.get(
            Panel.URL + '/api/client',
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Panel.API_KEY}"
            }
        )

        if res.status != 200:
            raise ApiError(f'[Global] Failed to fetch server list: {res.status}')

        return await res.json()

    @staticmethod
    async def start_monitor(guild_id):
        try:
            server = Guild.get_instance(guild_id)

            for server_id, panel in server.panel.servers.items():
                channel_id = panel.channel_id

                if not channel_id:
                    continue

                panel = Panel(server_id)

                try:
                    details = await panel.get_server_details()
                    resources = await panel.get_server_resources()
                except ApiError as error:
                    log.warn(error)
                    return

                identifier = details['attributes']['identifier']
                name = details['attributes']['name']
                description = details['attributes']['description']

                try:
                    state = resources['attributes']['current_state']
                except (KeyError, TypeError):
                    state = 'offline'

                embed = Embed(timestamp=datetime.now())
                embed.set_author(name, url=Panel.URL + '/server/' + server_id)
                embed.set_description(description)
                embed.set_thumbnail(ICONS['green'] if state == 'running' else ICONS['red'])
                embed.set_footer(identifier)

                image_url = panel.get_variable('DISCORD_IMAGE_URL')

                if image_url and validators.url(image_url):
                    embed.set_image(image_url)

                if state != 'offline':
                    state = resources['attributes']['current_state']

                    current_cpu_usage = resources['attributes']['resources']['cpu_absolute']
                    current_cpu_usage = f"{current_cpu_usage:.2f}"
                    max_cpu_usage = details['attributes']['limits']['cpu']

                    current_memory_usage = resources['attributes']['resources']['memory_bytes'] / 1024 / 1024
                    current_memory_usage = f"{current_memory_usage:,.0f}"
                    max_memory_usage = details['attributes']['limits']['memory']
                    max_memory_usage = f'{max_memory_usage:,.0f}' if max_memory_usage != 0 else 0

                    uptime = resources['attributes']['resources']['uptime']

                    embed.add_field('Status', state.title())
                    embed.add_field('Uptime', format_uptime(uptime))
                    embed.add_field('\u200b', '\u200b')
                    embed.add_field('CPU Usage', f"{current_cpu_usage} / {max_cpu_usage} %" if max_cpu_usage != 0 else f"{current_cpu_usage} %")
                    embed.add_field('Memory Usage', f"{current_memory_usage} / {max_memory_usage} MB" if max_memory_usage != 0 else f"{current_memory_usage} MB")
                    embed.add_field('\u200b', '\u200b')

                    if 'minecraft' in name.lower():
                        await panel.add_minecraft(embed)
                else:
                    embed.add_field('Status', state.title())

                channel = bot.get_channel(channel_id)
                server = Guild.get_instance(channel.guild.id)

                message_id = server.panel.servers[server_id].message_id

                try:
                    message = await channel.fetch_message(message_id) if message_id else None
                except discord.NotFound:
                    message = None

                try:
                    if not message:
                        message = await channel.send(embed=embed)
                        server.panel.servers[server_id].message_id = message.id
                        await server.save_changes()
                    else:
                        await message.edit(embed=embed)
                except discord.HTTPException as error:
                    log.error(error)
        except asyncio.TimeoutError:
            log.error('Panel server timeout!')
        except asyncio.CancelledError:
            pass

    async def add_minecraft(self, embed):
        server_ip = self.get_default_ip()

        if not server_ip:
            return

        try:
            res = await self.session.get(self.MCSTATUS_API + '/' + server_ip)
            data = await res.json()

            if not data['online']:
                return

            players = [player["name_clean"] for player in data["players"]["list"]]

            embed.add_field(
                'Players',
                '```\n' + '\n'.join(players) + '\n```'
                if len(players) > 0 else
                '*```No players online```*'
            )
        except (ContentTypeError, asyncio.TimeoutError) as error:
            pass

    def get_variable(self, key, default=None):
        try:
            variable = find(
                lambda data: data['attributes']['env_variable'] == key,
                self.details['attributes']['relationships']['variables']['data']
            )['attributes']

            return variable['server_value'] or variable['default_value']
        except (KeyError, TypeError):
            return default

    def get_default_ip(self):
        try:
            allocation = find(
                lambda data: data['attributes']['is_default'] is True,
                self.details['attributes']['relationships']['allocations']['data']
            )['attributes']

            return allocation['ip'] + ':' + str(allocation['port'])
        except (KeyError, TypeError) as e:
            return None

    @staticmethod
    def start_listener(guild_id: int):
        server = Guild.get_instance(guild_id)

        if bot.scheduler.get_job('panel-' + str(guild_id)):
            return

        servers = {k: v for k, v in server.panel.servers.items() if v.channel_id}

        if len(servers) > 0:
            next_run_time = datetime.now() + timedelta(seconds=5 * len(bot.scheduler.get_jobs()))

            bot.scheduler.add_job(
                id='panel-' + str(guild_id),
                func=Panel.start_monitor,
                trigger='interval',
                minutes=1,
                kwargs={
                    'guild_id': guild_id,
                },
                next_run_time=next_run_time
            )
            log.info(f'Auto started job panel-{guild_id}')