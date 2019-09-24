from __future__ import annotations

import logging
from typing import cast

from addict import Dict
from pymongo import MongoClient

from . import env
from .helpers.log import Log

log = cast(Log, logging.getLogger(__name__))


class GuildDatabase:
    def __init__(self, db: MongoClient, guild_id: int) -> None:
        self.db = db
        self.guild_id = str(guild_id)
        self.refresh_config()

    def refresh_config(self) -> GuildDatabase:
        self.config = Dict(self.db.servers.find_one({"server_id": self.guild_id}))
        return self

    def update_config(self) -> GuildDatabase:
        if isinstance(self.config, Dict):
            self.config = self.config.to_dict()
        self.db.servers.update_one({"server_id": self.guild_id}, {"$set": self.config})
        return self.refresh_config()


class BotDatabase:
    def __init__(self, db: MongoClient) -> None:
        self.db = db
        self.refresh_settings()

    def refresh_settings(self) -> BotDatabase:
        self.settings = Dict(self.db.settings.find_one())
        return self

    def update_settings(self) -> BotDatabase:
        if isinstance(self.settings, Dict):
            self.settings = self.settings.to_dict()
        self.db.settings.update_one({}, {"$set": self.settings})
        return self.refresh_settings()


class Database:
    def __init__(self) -> None:
        self.db = self.load_database()

    def load_database(self) -> MongoClient:
        username = env.str("DB_USER")
        password = env.str("DB_PASS")
        url = env.str("DB_HOST").split(":")
        name = env.str("DB_NAME")

        client = MongoClient(
            host=url[0],
            port=int(url[1]),
            username=username,
            password=password,
            authSource=name,
            retryWrites=False,
        )
        log.info(f"MongoDB connection established on {':'.join(url)}")

        return client[name]

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
                    "autoplay": False,
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
