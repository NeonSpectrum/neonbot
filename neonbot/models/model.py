from __future__ import annotations

from motor.core import AgnosticCollection, AgnosticDatabase


class Model:
    client: AgnosticDatabase = None

    def __init__(self) -> None:
        self.db: AgnosticDatabase = Model.client
        self.data = {}
        self.table = None
        self.where = {}

    @property
    def collection(self) -> AgnosticCollection:
        return self.db.get_collection(self.table)

    async def refresh(self) -> Model:
        self.data = await self.collection.find_one(self.where)
        return self

    async def insert(self, value: any) -> Model:
        await self.collection.insert_one(value)
        await self.refresh()
        return self

    def get(self, key: str = None, default: any = None) -> any:
        if key is None:
            return self.data

        keys = key.split(".")
        value = None

        for key in keys:
            value = value.get(key, default) if value else self.data.get(key)

        if value is None:
            value = default

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
        await self.collection.update_one(self.where, {"$set": self.data})
        await self.refresh()

    async def update(self, value: any, *, where: dict = None):
        where = self.where if not where else {**self.where, **where}

        await self.collection.update_one(where, {"$set": value})

        await self.refresh()

    @staticmethod
    def set_client(client: AgnosticDatabase):
        Model.client = client
