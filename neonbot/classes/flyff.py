import math
from datetime import datetime, timedelta

import discord
from envparse import env

from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.models.guild import GuildModel
from neonbot.utils import log
from neonbot.utils.constants import ICONS


class Flyff:
    IP_ADDRESS = env.str('FLYFF_IP_ADDRESS')

    def __init__(self, guild_id: int):
        self.guild_id = guild_id

    def calculate_next_spawn(self, initial_interval, interval):
        server = GuildModel.get_instance(self.guild_id)
        world_start_time = server.flyff.world_start_time

        current_time = datetime.now()
        start_time = datetime.strptime(world_start_time, '%Y-%m-%d %I:%M %p')

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

        return int(next_spawn_time.timestamp())

    @staticmethod
    async def start_monitor(guild_id):
        server = GuildModel.get_instance(guild_id)
        flyff = Flyff(guild_id)

        embed = Embed(timestamp=datetime.now())
        embed.set_author('Emerald Flyff', icon_url=ICONS['emeraldflyff'])
        embed.set_thumbnail(ICONS['green'])

        timers = []

        for name, timer in server.flyff.timers.items():
            spawn_time = flyff.calculate_next_spawn(timer.initial_interval, timer.interval)
            timers.append(f'- {name}: `<t:{spawn_time}:R>`')

        embed.add_field('Timer', '\n'.join(timers))

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

        if len(server.flyff.timers) > 0:
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
