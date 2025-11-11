from __future__ import annotations

from typing import Optional

from beanie import Document

from neonbot.utils import log


class SettingModel(Document):
    status: str
    activity_name: str
    activity_type: str

    class Settings:
        name = 'settings'
        use_cache = True

    @staticmethod
    async def get_instance() -> Optional[SettingModel]:
        return await SettingModel.find_one()

    @staticmethod
    async def initialize():
        settings = await SettingModel.find_one()

        if settings is None:
            log.info('Settings not found. Creating settings...')
            await SettingModel.create_default_collection()

    @staticmethod
    async def create_default_collection():
        await SettingModel(status='online', activity_type='listening', activity_name='my heartbeat').create()
