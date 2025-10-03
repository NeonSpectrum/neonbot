from datetime import datetime, timedelta

import discord
from durations_nlp import Duration
from envparse import env

from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.models.flyff import FlyffTimer
from neonbot.models.guild import GuildModel
from neonbot.utils import log
from neonbot.utils.constants import ICONS


class Flyff:
    IP_ADDRESS = env.str('FLYFF_IP_ADDRESS')

    def __init__(self, guild_id: int):
        self.guild_id = guild_id

    async def add_timer(self, name, initial_interval, interval):
        initial_interval = Duration(initial_interval).to_seconds()
        interval = Duration(interval).to_seconds()

        server = GuildModel.get_instance(self.guild_id)
        server.flyff.timers[name] = FlyffTimer(initial_interval=initial_interval, interval=interval)
        await server.save_changes()

    async def remove_timer(self, name):
        server = GuildModel.get_instance(self.guild_id)
        del server.flyff.timers[name]
        await server.save_changes()

    def calculate_next_spawn(self, initial_interval, interval):
        server = GuildModel.get_instance(self.guild_id)
        world_start_time = server.flyff.world_start_time

        now = datetime.now()

        start_time_obj = datetime.strptime(world_start_time, '%I:%M %p').time()

        start_datetime = datetime.combine(now.date(), start_time_obj)

        if start_datetime < now:
            start_datetime += timedelta(days=1)

        initial_alarm_time = start_datetime + timedelta(seconds=initial_interval)

        if now < initial_alarm_time:
            next_alarm = initial_alarm_time
        else:
            time_elapsed = now - initial_alarm_time
            intervals_passed = time_elapsed.total_seconds() // interval
            next_alarm = initial_alarm_time + timedelta(seconds=(intervals_passed + 1) * interval)

        return next_alarm


    @staticmethod
    async def start_monitor(guild_id):
        server = GuildModel.get_instance(guild_id)
        flyff = Flyff(guild_id)

        embed = Embed(timestamp=datetime.now())
        embed.set_thumbnail(ICONS['green'])

        for name, timer in server.flyff.timers.items():
            embed.add_field(name, flyff.calculate_next_spawn(timer.initial_interval, timer.interval))

        channel = bot.get_channel(server.flyff.channel_id)
        message_id = server.flyff.message_id
        server = GuildModel.get_instance(channel.guild.id)

        try:
            message = await channel.fetch_message(message_id) if message_id else None
        except discord.NotFound:
            message = None

        try:
            if not message:
                message = await channel.send(embed=embed)
                server.flyff.message_id = message.id
                await server.save_changes()
            else:
                await message.edit(embed=embed)
        except discord.HTTPException as error:
            log.error(error)

    @staticmethod
    def start_listener(guild_id: int):
        server = GuildModel.get_instance(guild_id)

        if bot.scheduler.get_job('flyff-' + str(guild_id)):
            return

        servers = {k: v for k, v in server.flyff.timers.items() if v.channel_id}

        if len(servers) > 0:
            next_run_time = datetime.now() + timedelta(seconds=5 * len(bot.scheduler.get_jobs()))

            bot.scheduler.add_job(
                id='flyff-' + str(guild_id),
                func=Flyff.start_monitor,
                trigger='interval',
                minutes=1,
                kwargs={
                    'guild_id': guild_id,
                },
                next_run_time=next_run_time,
            )
            log.info(f'Auto started job flyff-{guild_id}')
