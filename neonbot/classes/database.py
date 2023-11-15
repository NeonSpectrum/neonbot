from __future__ import annotations

import asyncio
from time import time
from typing import List

import discord
from beanie import init_beanie
from beanie.odm.operators.find.comparison import In
from envparse import env
from motor.motor_asyncio import AsyncIOMotorClient as MotorClient

from neonbot.models.guild import Guild
from neonbot.models.setting import Setting
from neonbot.utils import log


class Database:
    def __init__(self, bot):
        self.client = None
        self.bot = bot
        self.settings = None
        self.db = None

    async def initialize(self) -> Database:
        mongo_url = env.str("MONGO_URL")
        db_name = env.str("MONGO_DBNAME")
        start_time = time()

        log.info(f"Connecting to Database...")
        client = MotorClient(mongo_url, ssl=True)
        self.db = client.get_database(db_name)
        await init_beanie(database=self.db, document_models=[Guild, Setting])
        log.info(f"MongoDB connection established in {(time() - start_time):.2f}s")

        await Setting.initialize()

        return self

    async def get_guilds(self, guilds: list) -> None:
        guild_ids = [guild.id for guild in guilds]
        existing_guild_ids = [server.id for server in await Guild.find(In(Guild.id, guild_ids)).to_list()]
        new_guild = [guild for guild in guilds if guild.id not in existing_guild_ids]

        # for guild in new_guild:
        #     log.info(f"Creating database for {guild}...")
        #     await Guild.create_default_collection(guild.id)

        await asyncio.gather(*[self.cache_guild(guild) for guild in guilds])

    async def cache_guild(self, guild):
        log.info(f"Caching guild settings: {guild} ({guild.id})")
        await self.start_migration(guild.id)
        await Guild.create_instance(guild.id)

    async def start_migration(self, guild_id: int):
        guild = await self.db.servers.find_one({'_id': guild_id})

        if 'channel' in guild:
            guild['channel_log'] = {
                'connect': guild['channel']['voice_log'],
                'disconnect': guild['channel']['voice_log'],
                'mute': None,
                'deafen': None,
                'server_deafen': None,
                'server_mute': None,
                'status': getattr(guild['channel'], 'status_log', None),
                'activity': getattr(guild['channel'], 'activity_log', None)
            }

            guild['chatgpt']['channel_id'] = guild['channel']['chatgpt']

            del guild['channel']

            await self.db.guilds.insert_one(guild)
