from __future__ import annotations

from typing import Optional

from beanie import Document

from neonbot.utils import log


class Setting(Document):
    status: str
    activity_name: str
    activity_type: str

    class Settings:
        name = 'settings'
        use_cache = True

    @staticmethod
    async def get_instance() -> Optional[Setting]:
        return await Setting.find_one()

    @staticmethod
    async def initialize():
        settings = await Setting.find_one()

        if settings is None:
            log.info('Settings not found. Creating settings...')
            await Setting.create_default_collection()

    @staticmethod
    async def create_default_collection():
        await Setting(status="online", activity_type="listening", activity_name="my heartbeat").create()
