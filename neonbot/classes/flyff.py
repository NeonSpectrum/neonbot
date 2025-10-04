import math
from datetime import datetime, timedelta, timezone

import discord
from envparse import env

from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.models.guild import GuildModel
from neonbot.utils import log
from neonbot.utils.constants import ICONS
from neonbot.utils.functions import check_ip_online_socket


class Flyff:
    IP_ADDRESS = env.str('FLYFF_IP_ADDRESS')
    LAST_ALERT_MESSAGE = None

    def calculate_next_spawn(self, initial_interval, interval, func):
        world_start_time = bot.flyff_settings.world_start_time

        current_time = datetime.now()
        start_time = datetime.strptime(world_start_time, '%Y-%m-%d %I:%M:%S %p')

        initial_interval = initial_interval / 60
        interval = interval / 60

        first_spawn_time = start_time + timedelta(minutes=initial_interval)

        if current_time <= first_spawn_time:
            return first_spawn_time

        time_since_first_spawn = current_time - first_spawn_time

        passed_intervals_count = math.floor(
            time_since_first_spawn.total_seconds() / (interval * 60)
        )

        last_passed_spawn_time = first_spawn_time + timedelta(minutes=passed_intervals_count * interval)

        if current_time == last_passed_spawn_time:
            next_spawn_time = last_passed_spawn_time + timedelta(minutes=interval)
        else:
            next_spawn_time = last_passed_spawn_time + timedelta(minutes=interval)

        if func(passed_intervals_count):
            next_spawn_time += timedelta(minutes=interval)

        return int(next_spawn_time.timestamp())

    async def refresh_status(self):
        ip, port = Flyff.IP_ADDRESS.split(':')
        status = await check_ip_online_socket(ip, port)

        embed = Embed(timestamp=datetime.now())
        embed.set_author('Emerald Flyff', icon_url=ICONS['emeraldflyff'])
        embed.set_thumbnail(ICONS['green'] if status else ICONS['red'])

        timers = []

        for name, timer in bot.flyff_settings.timers.items():
            spawn_time = self.calculate_next_spawn(
                timer.initial_interval, timer.interval,
                lambda count: (name == 'Karvan' and count % 2 == 0)
                              or (name == 'Clockworks' and count % 2 == 1)
            )

            timers.append(f'- {name}: <t:{spawn_time}:t> <t:{spawn_time}:R>')

        embed.add_field('Timer', '\n'.join(timers), inline=False)

        status_channel = bot.get_channel(bot.flyff_settings.status_channel_id)

        if status_channel:
            message_id = bot.flyff_settings.status_message_id
            server = GuildModel.get_instance(status_channel.guild.id)

            try:
                message = await status_channel.fetch_message(message_id) if message_id else None
            except discord.NotFound:
                message = None

            try:
                if not message:
                    message = await status_channel.send(embed=embed)
                    server.flyff.status_message_id = message.id
                    await server.save_changes()
                else:
                    await message.edit(embed=embed)
            except discord.HTTPException as error:
                log.error(error)

    async def check_next_alert(self):
        alert_message = None

        for name, timer in bot.flyff_settings.timers.items():
            spawn_time = self.calculate_next_spawn(
                timer.initial_interval, timer.interval,
                lambda count: (name == 'Karvan' and count % 2 == 0)
                              or (name == 'Clockworks' and count % 2 == 1)
            )

            current_time = datetime.now(timezone.utc)
            spawn_time = datetime.fromtimestamp(spawn_time).astimezone(timezone.utc)

            if abs(current_time - spawn_time) <= timedelta(seconds=5):
                alert_message = f'World Boss `{name}` will spawn now.'
            elif abs(current_time - spawn_time) <= timedelta(minutes=5):
                alert_message = f'World Boss `{name}` will spawn in 5 minutes.'

        alert_channels = [bot.get_channel(channel_id) for channel_id in bot.flyff_settings.alert_channels]

        for channel in alert_channels:
            if alert_message != Flyff.LAST_ALERT_MESSAGE:
                await channel.send('@everyone', embed=Embed(alert_message))

        Flyff.LAST_ALERT_MESSAGE = alert_message

    @staticmethod
    async def start_status_monitor():
        flyff = Flyff()
        await flyff.refresh_status()

    @staticmethod
    async def start_alert_monitor():
        flyff = Flyff()
        await flyff.check_next_alert()

    @staticmethod
    def start_listener(guild_id: int):
        if bot.scheduler.get_job('flyff-monitor'):
            return

        bot.scheduler.add_job(
            id='flyff-status-monitor',
            func=Flyff.start_status_monitor,
            trigger='interval',
            minutes=1,
        )
        log.info(f'Auto started job flyff-{guild_id}')

        bot.scheduler.add_job(
            id='flyff-alert-monitor',
            func=Flyff.start_status_monitor,
            trigger='interval',
            minutes=1,
        )
        log.info(f'Auto started job flyff-{guild_id}')
