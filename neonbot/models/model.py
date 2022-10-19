from __future__ import annotations

import asyncio


class Model:
    client = None

    def __init__(self) -> None:
        self.db = Model.client
        self.data = {}
        self.table = None
        self.where = {}

        asyncio.create_task(self.watch_collection())

    async def watch_collection(self):
        async with self.db[self.table].watch([{'$match': self.where}]):
            await self.refresh()

    async def refresh(self) -> Model:
        self.data = await self.db[self.table].find_one(self.where)
        return self

    async def insert(self, value: any) -> Model:
        await self.db[self.table].insert_one(value)
        await self.refresh()
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
                existing = current[key] if key in current else {}
                current[key] = {**existing, **value} if isinstance(value, dict) else value

    async def save(self):
        await self.db[self.table].update_one(self.where, {"$set": self.data})
        await self.refresh()

    async def update(self, config: any):
        await self.db[self.table].update_one(self.where, {"$set": config})
        await self.refresh()

    @staticmethod
    def set_client(client):
        Model.client = client
