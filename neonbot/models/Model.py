from pymongo import MongoClient


class Model:
    def __init__(self, db: MongoClient) -> None:
        self.db = db
        self.data = {}
        self.table = None
        self.where = {}

    def refresh(self) -> None:
        self.data = self.db[self.table].find_one(self.where)

    def get(self, key: str, default: any = None) -> any:
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

    def save(self):
        self.db.servers.update_one(self.where, {"$set": self.data})
        self.refresh()

    def update(self, config: any):
        self.db.servers.update_one(self.where, {"$set": config})
        self.refresh()
