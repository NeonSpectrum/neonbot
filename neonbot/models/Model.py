from pymongo import MongoClient


class Model:
    def __init__(self, db: MongoClient) -> None:
        self.db = db
        self.data = {}
        self.table = None
        self.where = {}

    def refresh(self) -> None:
        self.data = self.db[self.table].find_one(self.where)

    def get(self, key: str, default: any = "") -> any:
        return self.data.get(key, default)

    def set(self, key: str, value: any) -> None:
        if isinstance(value, dict):
            self.data[key] = {**self.data[key], **value}
        else:
            self.data[key] = value

    def save(self):
        self.db.servers.update_one(self.where, {"$set": self.data})
        self.refresh()

    def update(self, config: any):
        self.db.servers.update_one(self.where, {"$set": config})
        self.refresh()
