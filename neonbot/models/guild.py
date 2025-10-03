from __future__ import annotations

from typing import Optional

from beanie import Document
from beanie.odm.queries.find import FindOne

from neonbot.enums import Repeat
from neonbot.models.channel_log import ChannelLogModel
from neonbot.models.chatgpt import ChatGPTModel
from neonbot.models.exchange_gift import ExchangeGiftModel
from neonbot.models.flyff import FlyffModel
from neonbot.models.music import MusicModel
from neonbot.models.panel import PanelModel

guilds = {}


class GuildModel(Document):
    id: int
    prefix: str
    channel_log: ChannelLogModel
    music: MusicModel
    exchange_gift: Optional[ExchangeGiftModel] = None
    chatgpt: Optional[ChatGPTModel] = None
    panel: Optional[PanelModel] = None
    flyff: Optional[FlyffModel] = None

    class Settings:
        name = 'guilds'
        use_cache = True
        use_state_management = True

    async def refresh(self) -> None:
        guilds[self.id] = await GuildModel.find_one(GuildModel.id == self.id)

    @staticmethod
    async def create_instance(guild_id: int) -> None:
        guilds[guild_id] = await GuildModel.find_one(GuildModel.id == guild_id)

    @staticmethod
    def get_instance(guild_id: int) -> Optional[GuildModel]:
        return guilds[guild_id]

    @staticmethod
    def get_model(guild_id: int) -> FindOne[GuildModel]:
        return GuildModel.find_one(GuildModel.id == guild_id)

    @staticmethod
    async def create_default_collection(guild_id: int):
        if await GuildModel.find_one(GuildModel.id == guild_id):
            return

        await GuildModel(
            id=guild_id,
            prefix='.',
            channel_log=ChannelLogModel(),
            music=MusicModel(volume=100, repeat=Repeat.OFF.value, shuffle=False, autoplay=False),
            exchange_gift=ExchangeGiftModel(members=[]),
            chatgpt=ChatGPTModel(chats=[]),
            panel=PanelModel(servers={}),
            flyff=FlyffModel()
        ).create()
