import asyncio
import math
from datetime import datetime, timedelta
from typing import List

import discord
from aiohttp import ClientTimeout
from envparse import env

from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.utils import log
from neonbot.utils.constants import ICONS
from neonbot.utils.functions import check_ip_online_socket


class Flyff:
    IP_ADDRESS = env.str('FLYFF_IP_ADDRESS')
    RESET_TIME = '06:00 PM'
    DOWNTIME_COUNT = 0

    def calculate_next_spawn(self, initial_interval, interval, func):
        world_start_time = bot.flyff_settings.world_start_time

        current_time = datetime.now()
        start_time = datetime.strptime(world_start_time, '%Y-%m-%d %I:%M:%S %p')

        initial_interval = initial_interval / 60
        interval = interval / 60

        first_spawn_time = start_time + timedelta(minutes=initial_interval)

        if current_time <= first_spawn_time:
            if func(1):
                first_spawn_time += timedelta(minutes=interval)
            return int(first_spawn_time.timestamp())

        time_since_first_spawn = current_time - first_spawn_time

        passed_intervals_count = math.floor(time_since_first_spawn.total_seconds() / (interval * 60))

        last_passed_spawn_time = first_spawn_time + timedelta(minutes=passed_intervals_count * interval)

        if current_time == last_passed_spawn_time:
            next_spawn_time = last_passed_spawn_time + timedelta(minutes=interval)
        else:
            next_spawn_time = last_passed_spawn_time + timedelta(minutes=interval)

        if func(passed_intervals_count):
            next_spawn_time += timedelta(minutes=interval)

        return int(next_spawn_time.timestamp())

    async def refresh_status(self, only_channel_id=None):
        world_start_time = bot.flyff_settings.world_start_time
        embed = Embed(timestamp=datetime.now())
        embed.set_author('Emerald Flyff', icon_url=ICONS['emeraldflyff'])
        embed.set_thumbnail(ICONS['green'] if bot.flyff_settings.status else ICONS['red'])

        timers = []
        events = []

        if world_start_time:
            server_start_time = datetime.strptime(world_start_time, '%Y-%m-%d %I:%M:%S %p')
            server_start_time = int(server_start_time.timestamp())
            next_reset_time = int(self.get_next_reset_time(Flyff.RESET_TIME).timestamp())
            for name, timer in bot.flyff_settings.timers.items():
                spawn_time = self.calculate_next_spawn(
                    timer.initial_interval,
                    timer.interval,
                    lambda count: (name == 'Karvan' and count % 2 == 0) or (name == 'Clockworks' and count % 2 == 1),
                )

                timers.append(f'- {name}: <t:{spawn_time}:T> <t:{spawn_time}:R>')

            for name, time_list in bot.flyff_settings.fixed_timers.items():
                next_time = int(self.get_next_nearest_time(time_list).timestamp())

                events.append(f'- {name}: <t:{next_time}:t> <t:{next_time}:R>')

            embed.add_field(
                'Server',
                '\n'.join(
                    [
                        f'- Start time: <t:{server_start_time}:D> <t:{server_start_time}:T>',
                        f'- Next Reset: <t:{next_reset_time}:t> <t:{next_reset_time}:R>',
                    ]
                ),
                inline=False,
            )
            embed.add_field('Boss Timer', '\n'.join(timers), inline=False)
            embed.add_field('Event', '\n'.join(events), inline=False)
        else:
            embed.add_field('Server', '```OFFLINE```', inline=False)

        for channel_id, message_id in bot.flyff_settings.status_channels.items():
            if only_channel_id and only_channel_id != channel_id:
                continue

            channel = bot.get_channel(channel_id)

            try:
                message = await channel.fetch_message(message_id) if message_id else None
            except discord.NotFound:
                message = None

            try:
                if not message:
                    message = await channel.send(embed=embed)

                    bot.flyff_settings.status_channels[channel_id] = message.id
                    await bot.flyff_settings.save_changes()
                else:
                    await message.edit(embed=embed)
            except discord.HTTPException as error:
                log.error(error)

    async def check_next_alert(self):
        if not bot.flyff_settings.world_start_time:
            return

        alert_message = None

        for name, timer in bot.flyff_settings.timers.items():
            spawn_time = self.calculate_next_spawn(
                timer.initial_interval,
                timer.interval,
                lambda count: (name == 'Karvan' and count % 2 == 0) or (name == 'Clockworks' and count % 2 == 1),
            )

            current_time = datetime.now().replace(tzinfo=None)
            spawn_time = datetime.fromtimestamp(spawn_time)

            if abs(current_time - spawn_time) <= timedelta(seconds=5):
                alert_message = f'**{name}** will spawn **soon**!'
            elif abs(current_time - spawn_time) <= timedelta(minutes=5):
                alert_message = f'**{name}** will spawn in **5 minutes**.'

        for name, time_list in bot.flyff_settings.fixed_timers.items():
            current_time = datetime.now()

            next_time = self.get_next_nearest_time(time_list)

            if abs(current_time - next_time) <= timedelta(seconds=5):
                alert_message = f'**{name}** will start **soon**!'
            elif abs(current_time - next_time) <= timedelta(minutes=5):
                alert_message = f'**{name}** will start in **5 minutes**.'

        if not alert_message or alert_message == bot.flyff_settings.last_alert_message:
            return

        alert_channels = [bot.get_channel(alert.channel_id) for alert in bot.flyff_settings.alert_channels]
        tasks = []

        for channel in alert_channels:
            if alert_message != bot.flyff_settings.last_alert_message:
                tasks.append(channel.send(f'@everyone {alert_message}'))

        for _, webhook_url in bot.flyff_settings.webhooks.items():
            tasks.append(self.trigger_webhook(webhook_url, alert_message))

        await asyncio.gather(*tasks)
        bot.flyff_settings.last_alert_message = alert_message
        await bot.flyff_settings.save_changes()

    def get_next_nearest_time(self, times: List[str]):
        current_datetime = datetime.now()
        current_date = current_datetime.date()

        scheduled_times = []
        for time_str in times:
            dt_object = datetime.strptime(time_str, '%I:%M %p')
            scheduled_times.append(dt_object.time())

        scheduled_times.sort()

        current_time_obj = current_datetime.time()

        for scheduled_time_obj in scheduled_times:
            if scheduled_time_obj > current_time_obj:
                return datetime.combine(current_date, scheduled_time_obj)

        next_day_time_obj = scheduled_times[0]

        next_day_date = current_date + timedelta(days=1)

        return datetime.combine(next_day_date, next_day_time_obj)

    def get_next_reset_time(self, time_str):
        now = datetime.now()
        time = datetime.strptime(time_str, '%I:%M %p').time()

        if now.time() >= time:
            tomorrow = now.date() + timedelta(days=1)
            next_time = datetime.combine(tomorrow, time)
        else:
            next_time = datetime.combine(now.date(), time)

        return next_time

    async def trigger_webhook(self, url, message):
        try:
            await bot.session.post(url, json={'message': message}, timeout=ClientTimeout(total=2))
        except asyncio.exceptions.TimeoutError as e:
            pass
        except Exception as e:
            log.error(f'An unexpected error occurred: {e}')

    @staticmethod
    async def start_status_monitor():
        flyff = Flyff()
        await flyff.refresh_status()

    @staticmethod
    async def start_alert_monitor():
        flyff = Flyff()
        await flyff.check_next_alert()

    @staticmethod
    async def start_ping_monitor():
        old_status = bot.flyff_settings.status
        ip, port = Flyff.IP_ADDRESS.split(':')
        status = await check_ip_online_socket(ip, port, 30)

        embed = None

        if not old_status and status:
            embed = Embed(f'`{datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")}` Server up!')
        elif old_status and not status:
            embed = Embed(f'`{datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")}` Server went down.')

        if not status and bot.flyff_settings.world_start_time:
            Flyff.DOWNTIME_COUNT += 1

            if Flyff.DOWNTIME_COUNT >= 10:
                bot.flyff_settings.world_start_time = None
                await bot.flyff_settings.save_changes()

        if not embed:
            return

        ping_channels = [bot.get_channel(ping.channel_id) for ping in bot.flyff_settings.ping_channels]
        tasks = []

        for channel in ping_channels:
            tasks.append(channel.send(embed=embed))

        await asyncio.gather(*tasks)

        bot.flyff_settings.status = status
        await bot.flyff_settings.save_changes()

    @staticmethod
    def start_listener():
        if bot.scheduler.get_job('flyff-monitor'):
            return

        next_run_time = datetime.now() + timedelta(seconds=5 * len(bot.scheduler.get_jobs()))

        bot.scheduler.add_job(
            id='flyff-status-monitor',
            func=Flyff.start_status_monitor,
            trigger='interval',
            minutes=1,
            next_run_time=next_run_time,
        )
        log.info(f'Auto started job flyff-status-monitor')

        bot.scheduler.add_job(
            id='flyff-alert-monitor',
            func=Flyff.start_alert_monitor,
            trigger='interval',
            seconds=5,
            next_run_time=next_run_time,
        )
        log.info(f'Auto started job flyff-alert-monitor')

        bot.scheduler.add_job(
            id='flyff-ping-monitor',
            func=Flyff.start_ping_monitor,
            trigger='interval',
            seconds=5,
            next_run_time=next_run_time,
        )
        log.info(f'Auto started job flyff-ping-monitor')
