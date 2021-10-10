from __future__ import annotations

import logging
import ssl
from time import time
from typing import cast

from pymongo import MongoClient

from .env import env
from .helpers.log import Log
from .models.Guild import Guild
from .models.Settings import Settings

log = cast(Log, logging.getLogger(__name__))


class Database:
    def __init__(self) -> None:
        self.db = self.load_database()
        self.servers = {}
        self.settings = None

    def load_database(self) -> MongoClient:
        mongo_url = env.str("MONGO_URL")
        db_name = env.str("MONGO_DBNAME")
        client = MongoClient(mongo_url, ssl=True, ssl_cert_reqs=ssl.CERT_NONE)

        start_time = time()
        log.info(f"Connecting to Database...")
        client.admin.command("ismaster")
        log.info(f"MongoDB connection established in {(time() - start_time):.2f}s")

        return client[db_name]

    def process_database(self, guilds: list) -> None:
        for guild in guilds:
            count = self.db.servers.find({"server_id": str(guild.id)}).count()

            if count == 0:
                log.info(f"Creating database for {guild}...")
                self.create_collection(guild.id)

    def create_collection(self, guild_id: int) -> None:
        self.db.servers.insert_one(
            {
                "server_id": str(guild_id),
                "prefix": env.str("DEFAULT_PREFIX", "."),
                "deleteoncmd": True,
                "aliases": [],
                "channel": {
                    "log": None,
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
