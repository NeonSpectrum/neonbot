from __future__ import annotations

import asyncio
from time import time
from typing import List

import discord
from envparse import env
from motor.motor_asyncio import AsyncIOMotorClient as MotorClient

from neonbot.models.guild import Guild
from neonbot.models.model import Model
from neonbot.models.settings import Settings
from neonbot.utils import log


class Database:
    def __init__(self, bot):
        self.client = None
        self.bot = bot
        self.servers = {}
        self.settings = None

    def initialize(self) -> Database:
        mongo_url = env.str("MONGO_URL")
        db_name = env.str("MONGO_DBNAME")
        start_time = time()

        log.info(f"Connecting to Database...")
        client = MotorClient(mongo_url, ssl=True)
        self.client = client.get_database(db_name)
        log.info(f"MongoDB connection established in {(time() - start_time):.2f}s")

        Model.set_client(self.client)

        return self

    async def get_settings(self):
        self.settings = Settings()
        await self.settings.refresh()

        if self.settings.get() is None:
            log.info('Settings not found. Creating settings...')
            await self.settings.create_default_collection()

        return self.settings

    async def get_guilds(self, guilds: list) -> None:
        guild_ids = [str(guild.id) for guild in guilds]
        existing_guild_ids = [guild["server_id"] async for guild in
                              self.client.servers.find({"server_id": {"$in": guild_ids}})]
        new_guild = [guild for guild in guilds if str(guild.id) not in existing_guild_ids]

        for guild in new_guild:
            log.info(f"Creating database for {guild}...")
            await Guild.get_instance(guild.id).create_default_collection()

        await self.cache_guilds(guilds)

    async def cache_guilds(self, guilds: List[discord.Guild]):
        async def cache(guild):
            log.info(f"Caching guild settings: {guild}")
            await Guild.get_instance(guild.id).refresh()

        await asyncio.gather(*[cache(guild) for guild in guilds])
