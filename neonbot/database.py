from __future__ import annotations

import logging
from time import time
from typing import cast

from addict import Dict
from pymongo import MongoClient

from .env import env
from .helpers.log import Log

log = cast(Log, logging.getLogger(__name__))


class GuildDatabase:
    def __init__(self, db: MongoClient, guild_id: int) -> None:
        self.db = db
        self.guild_id = str(guild_id)
        self.refresh()

    def refresh(self) -> GuildDatabase:
        self.config = Dict(self.db.servers.find_one({"server_id": self.guild_id}))
        return self

    def update(self) -> GuildDatabase:
        if isinstance(self.config, Dict):
            self.config = self.config.to_dict()
        self.db.servers.update_one({"server_id": self.guild_id}, {"$set": self.config})
        return self.refresh()


class BotDatabase:
    def __init__(self, db: MongoClient) -> None:
        self.db = db
        self.refresh()

    def refresh(self) -> BotDatabase:
        self.settings = Dict(self.db.settings.find_one())
        return self

    def update(self) -> BotDatabase:
        if isinstance(self.settings, Dict):
            self.settings = self.settings.to_dict()
        self.db.settings.update_one({}, {"$set": self.settings})
        return self.refresh()


class Database:
    def __init__(self) -> None:
        self.db = self.load_database()

    def load_database(self) -> MongoClient:
        mongo_url = env.str("MONGO_URL")
        db_name = env.str("MONGO_DBNAME")
        client = MongoClient(mongo_url)

        start_time = time()
        log.info(f"Connecting to Database...")
        client.admin.command("ismaster")
        log.info(f"MongoDB connection established in {(time() - start_time):.2f}s")
        return client[db_name]

    def process_database(self, guilds: list) -> None:
        for guild in guilds:
            count = self.db.servers.find({"server_id": str(guild.id)}).count

            if count == 0:
                self.create_collection(guild.id)

    def create_collection(self, guild_id: int) -> None:
        self.db.servers.insert_one(
            {
                "server_id": str(guild_id),
                "prefix": env.str("PREFIX"),
                "deleteoncmd": False,
                "strictmode": False,
                "aliases": [],
                "channel": {},
                "music": {
                    "volume": 100,
                    "repeat": "off",
                    "autoresume": False,
                    "roles": {},
                },
            }
        )
        self.db.servers.insert_one(
            {"status": "online", "game": {"type": "WATCHING", "name": "NANI?!"}}
        )

    def get_guild(self, guild_id: int) -> GuildDatabase:
        return GuildDatabase(self.db, guild_id)

    def get_settings(self) -> BotDatabase:
        return BotDatabase(self.db)
