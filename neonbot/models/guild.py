from __future__ import annotations

from typing import Optional

from beanie import Document
from beanie.odm.queries.find import FindOne

from neonbot.enums import Repeat
from neonbot.models.channel_log import ChannelLog
from neonbot.models.chatgpt import ChatGPT
from neonbot.models.exchange_gift import ExchangeGift
from neonbot.models.music import Music
from neonbot.models.panel import Panel

guilds = {}


class Guild(Document):
    id: int
    prefix: str
    channel_log: ChannelLog
    music: Music
    exchange_gift: Optional[ExchangeGift] = None
    chatgpt: Optional[ChatGPT] = None
    panel: Optional[Panel] = None

    class Settings:
        name = 'guilds'
        use_cache = True
        use_state_management = True

    async def refresh(self) -> None:
        guilds[self.id] = await Guild.find_one(Guild.id == self.id)

    @staticmethod
    async def create_instance(guild_id: int) -> None:
        guilds[guild_id] = await Guild.find_one(Guild.id == guild_id)

    @staticmethod
    def get_instance(guild_id: int) -> Optional[Guild]:
        return guilds[guild_id]

    @staticmethod
    def get_model(guild_id: int) -> FindOne[Guild]:
        return Guild.find_one(Guild.id == guild_id)

    @staticmethod
    async def create_default_collection(guild_id: int):
        if await Guild.find_one(Guild.id == guild_id):
            return

        await Guild(
            id=guild_id,
            prefix='.',
            channel_log=ChannelLog(),
            music=Music(volume=100, repeat=Repeat.OFF.value, shuffle=False),
            exchange_gift=ExchangeGift(members=[]),
            chatgpt=ChatGPT(chats=[]),
            panel=Panel()
        ).create()
