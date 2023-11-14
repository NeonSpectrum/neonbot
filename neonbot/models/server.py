from __future__ import annotations

from typing import Optional

from beanie import Document

from neonbot.enums import Repeat
from neonbot.models.channel import Channel
from neonbot.models.chatgpt import ChatGPT
from neonbot.models.exchange_gift import ExchangeGift
from neonbot.models.music import Music

servers = {}


class Server(Document):
    id: int
    prefix: str
    channel: Channel
    music: Music
    exchange_gift: Optional[ExchangeGift] = None
    chatgpt: Optional[ChatGPT] = None

    class Settings:
        name = 'servers'
        use_cache = True
        use_state_management = True

    async def refresh(self) -> None:
        servers[self.id] = await Server.find_one(Server.id == self.id)

    @staticmethod
    async def create_instance(guild_id: int) -> None:
        servers[guild_id] = await Server.find_one(Server.id == guild_id)

    @staticmethod
    def get_instance(guild_id: int) -> Optional[Server]:
        return servers[guild_id]

    @staticmethod
    async def create_default_collection(guild_id: int):
        if await Server.find_one(Server.id == guild_id):
            return

        await Server(
            id=guild_id,
            prefix='.',
            channel=Channel(voice_log=None, presence_log=None, msgdelete_log=None),
            music=Music(volume=100, repeat=Repeat.OFF.value, shuffle=False),
            exchange_gift=ExchangeGift(members=[]),
            chatgpt=ChatGPT(chats=[])
        ).create()

    @staticmethod
    async def start_migration(guild_id: int):
        server = await Server.find_one(Server.id == guild_id)

        if not server.exchange_gift:
            await server.set({'exchange_gift': ExchangeGift(members=[])})

        if not server.chatgpt:
            await server.set({'chatgpt': ChatGPT(chats=[])})

        if server.channel.presence_log:
            server.channel.status_log = server.channel.presence_log
            del server.channel.presence_log
            await server.save_changes()
