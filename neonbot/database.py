from __future__ import annotations

import asyncio
import logging
from time import time
from typing import cast, List

import nextcord
from motor.motor_asyncio import AsyncIOMotorClient as MotorClient

from .env import env
from .helpers.log import Log
from .models.Guild import Guild
from .models.Settings import Settings

log = cast(Log, logging.getLogger(__name__))


class Database:
    def __init__(self) -> None:
        self.db = None
        self.servers = {}
        self.settings = None

    def load(self) -> None:
        mongo_url = env.str("MONGO_URL")
        db_name = env.str("MONGO_DBNAME")
        start_time = time()

        log.info(f"Connecting to Database...")
        client = MotorClient(mongo_url, ssl=True)
        self.db = client.get_database(db_name)
        log.info(f"MongoDB connection established in {(time() - start_time):.2f}s")

    async def process_settings(self) -> Settings:
        settings = self.get_settings()
        await settings.refresh()

        if settings.get() is None:
            log.info('Creating settings...')
            await self.create_settings_collection()
            await settings.refresh()

        return settings

    async def process_database(self, guilds: list) -> None:
        guild_ids = [str(guild.id) for guild in guilds]
        existing_guild_ids = [guild['server_id'] async for guild in
                              self.db.servers.find({"server_id": {"$in": guild_ids}})]
        new_guild = [guild for guild in guilds if str(guild.id) not in existing_guild_ids]

        for guild in new_guild:
            log.info(f"Creating database for {guild}...")
            await self.create_guild_collection(guild.id)

        await self.cache_guilds(guilds)

    async def create_settings_collection(self) -> None:
        await self.db.settings.insert_one(
            {
                "game": {
                    "type": "LISTENING",
                    "name": "our favorite song"
                },
                "status": "online"
            }
        )

    async def create_guild_collection(self, guild_id: int) -> None:
        await self.db.servers.insert_one(
            {
                "server_id": str(guild_id),
                "prefix": env.str("DEFAULT_PREFIX", "."),
                "deleteoncmd": True,
                "aliases": [],
                "channel": {
                    "voice_log": None,
                    "presence_log": None,
                    "voicetts": None,
                    "debug": None,
                    "msgdelete": None,
                },
                "music": {
                    "volume": 100,
                    "repeat": "off",
                    "shuffle": False,
                },
            }
        )

    def get_guild(self, guild_id: int) -> Guild:
        if guild_id not in self.servers:
            self.servers[guild_id] = Guild(self.db, guild_id)
        return self.servers[guild_id]

    def get_settings(self) -> Settings:
        if not self.settings:
            self.settings = Settings(self.db)
        return self.settings

    async def cache_guilds(self, guilds: List[nextcord.Guild]):
        async def cache(guild):
            log.info(f"Caching guild settings: {guild}")
            await self.get_guild(guild.id).refresh()

        print()
        await asyncio.gather(*[cache(guild) for guild in guilds])
        print()
