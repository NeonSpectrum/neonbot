from __future__ import annotations

from typing import Dict, Optional, List

from beanie import Document
from pydantic import BaseModel

from neonbot.utils import log


class FlyffWebhookChannel(BaseModel):
    url: Optional[str]
    message_id: Optional[int]

class FlyffAlertChannel(BaseModel):
    channel_id: int

class FlyffPingChannel(BaseModel):
    channel_id: int

class FlyffTimer(BaseModel):
    initial_interval: int
    interval: int

class FlyffModel(Document):
    world_start_time: Optional[str] = None
    status_channels: Dict[int, Optional[int]] = {}
    webhook_channels: List[FlyffWebhookChannel] = []
    alert_channels: List[FlyffAlertChannel] = []
    ping_channels: List[FlyffPingChannel] = []
    timers: Dict[str, FlyffTimer] = {}
    fixed_timers: Dict[str, List] = {}
    last_alert_message: Optional[str] = ''
    webhooks: Dict[str, str] = []
    status: bool = False

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
            status_channels={},
            webhook_channels=[],
            alert_channels=[],
            ping_channels=[],
            timers={},
            fixed_timers={},
            last_alert_message='',
            webhooks=[],
            status=False
        ).create()
