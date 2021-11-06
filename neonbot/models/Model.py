from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient as MotorClient


class Model:
    def __init__(self, db: MotorClient) -> None:
        self.db = db
        self.data = {}
        self.table = None
        self.where = {}

    async def refresh(self) -> Model:
        self.data = await self.db[self.table].find_one(self.where)
        return self

    def get(self, key: str = None, default: any = None) -> any:
        if key is None:
            return self.data

        keys = key.split(".")
        value = None

        for key in keys:
            value = value.get(key, default) if value else self.data.get(key)

        return value

    def set(self, key: str, value: any) -> None:
        keys = key.split(".")
        current = None

        for i, key in enumerate(keys):
            if len(keys) == 1:
                current = self.data

            if current is None:
                current = self.data[key]
            elif i < len(keys) - 1:
                current = current[key]
            else:
                current[key] = {**current[key], **value} if isinstance(value, dict) else value

    async def save(self):
        await self.db.servers.update_one(self.where, {"$set": self.data})
        await self.refresh()

    async def update(self, config: any):
        await self.db.servers.update_one(self.where, {"$set": config})
        await self.refresh()
