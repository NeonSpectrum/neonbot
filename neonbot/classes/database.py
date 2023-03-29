from __future__ import annotations

import asyncio
from time import time
from typing import List

import discord
from beanie import init_beanie
from beanie.odm.operators.find.comparison import In
from envparse import env
from motor.motor_asyncio import AsyncIOMotorClient as MotorClient

from neonbot.models.server import Server
from neonbot.models.setting import Setting
from neonbot.utils import log


class Database:
    def __init__(self, bot):
        self.client = None
        self.bot = bot
        self.servers = {}
        self.settings = None

    async def initialize(self) -> Database:
        mongo_url = env.str("MONGO_URL")
        db_name = env.str("MONGO_DBNAME")
        start_time = time()

        log.info(f"Connecting to Database...")
        client = MotorClient(mongo_url, ssl=True)
        await init_beanie(database=client.get_database(db_name), document_models=[Server, Setting])
        log.info(f"MongoDB connection established in {(time() - start_time):.2f}s")

        await Setting.initialize()

        return self

    async def get_guilds(self, guilds: list) -> None:
        guild_ids = [guild.id for guild in guilds]
        existing_guild_ids = [server.id for server in await Server.find(In(Server.id, guild_ids)).to_list()]
        new_guild = [guild for guild in guilds if guild.id not in existing_guild_ids]

        for guild in new_guild:
            log.info(f"Creating database for {guild}...")
            await Server.create_default_collection(guild.id)

        await self.cache_guilds(guilds)

    async def cache_guilds(self, guilds: List[discord.Guild]):
        async def cache(guild):
            log.info(f"Caching guild settings: {guild} ({guild.id})")
            await Server.start_migration(guild.id)
            await Server.create_instance(guild.id)

        await asyncio.gather(*[cache(guild) for guild in guilds])
