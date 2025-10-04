from __future__ import annotations

from typing import Dict, Optional, List

from beanie import Document
from pydantic import BaseModel

from neonbot.utils import log


class FlyffStatusChannel(BaseModel):
    channel_id: str
    message_id: Optional[str]


class FlyffAlertChannel(BaseModel):
    channel_id: str

class FlyffTimer(BaseModel):
    initial_interval: int
    interval: int


class FlyffModel(Document):
    world_start_time: Optional[str] = None
    status_channels: List[FlyffStatusChannel] = []
    alert_channels: List[FlyffAlertChannel] = []
    timers: Dict[str, FlyffTimer]

    class Settings:
        name = 'flyff'
        use_cache = True
        use_state_management = True

    @staticmethod
    async def get_instance() -> Optional[FlyffModel]:
        return await FlyffModel.find_one()

    @staticmethod
    async def initialize():
        flyff = await FlyffModel.find_one()

        if flyff is None:
            log.info('Flyff settings not found. Creating flyff settings...')
            await FlyffModel.create_default_collection()

    @staticmethod
    async def create_default_collection():
        await FlyffModel(
            world_start_time=None,
            status_channels=[],
            alert_channels=[],
            timers={}
        ).create()
