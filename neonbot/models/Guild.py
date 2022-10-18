from __future__ import annotations

from envparse import env

from .model import Model
from ..enums import Repeat


class Guild(Model):
    servers = {}

    def __init__(self, guild_id: int) -> None:
        super().__init__()

        self.guild_id = guild_id
        self.table = "servers"
        self.where = {"server_id": str(guild_id)}

    @staticmethod
    def get_instance(guild_id):
        if guild_id not in Guild.servers.keys():
            Guild.servers[guild_id] = Guild(guild_id)

        return Guild.servers[guild_id]

    async def create_default_collection(self):
        await self.refresh()

        if self.get() is None:
            await self.db.servers.insert_one({
                "server_id": str(self.guild_id),
                "prefix": env.str("DEFAULT_PREFIX", default="."),
                "deleteoncmd": True,
                "aliases": [],
                "channel": {
                    "voice_log": None,
                    "presence_log": None,
                    "msgdelete_log": None,
                },
                "music": {
                    "volume": 100,
                    "repeat": Repeat.OFF.value,
                    "shuffle": False,
                },
            })
