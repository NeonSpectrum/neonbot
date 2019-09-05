from addict import Dict
from pymongo import MongoClient

from . import env
from .helpers import log


class Database:
    def load_database(self):
        username = env("DB_USER")
        password = env("DB_PASS")
        url = env("DB_HOST").split(":")
        name = env("DB_NAME")

        client = MongoClient(
            host=url[0],
            port=int(url[1]),
            username=username,
            password=password,
            authSource=name,
            retryWrites=False,
        )
        log.info(f"MongoDB connection established on {':'.join(url)}")

        self.db = client[name]

    def process_database(self, guilds):
        for guild in guilds:
            count = self.db.servers.find({"server_id": str(guild.id)}).count

            if count == 0:
                self.create_collection(guild.id)

    def create_collection(self, guild_id):
        self.db.servers.insert_one(
            {
                "server_id": str(guild_id),
                "prefix": env("PREFIX"),
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

    def get_guild(self, guild_id):
        return GuildDatabase(self.db, guild_id)

    def get_settings(self):
        return BotDatabase(self.db)


class GuildDatabase:
    def __init__(self, db, guild_id):
        self.db = db
        self.guild_id = str(guild_id)
        self.refresh_config()

    def refresh_config(self):
        self.config = Dict(self.db.servers.find_one({"server_id": self.guild_id}))
        return self

    def update_config(self):
        if isinstance(self.config, Dict):
            self.config = self.config.to_dict()
        self.db.servers.update_one({"server_id": self.guild_id}, {"$set": self.config})
        return self.refresh_config()


class BotDatabase:
    def __init__(self, db):
        self.db = db
        self.refresh_settings()

    def refresh_settings(self):
        self.settings = Dict(self.db.settings.find_one())
        return self

    def update_settings(self):
        if isinstance(self.settings, Dict):
            self.settings = self.settings.to_dict()
        self.db.settings.update_one({}, {"$set": self.settings})
        return self.refresh_settings()
