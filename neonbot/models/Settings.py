from pymongo import MongoClient

from .Model import Model


class Settings(Model):
    def __init__(self, db: MongoClient) -> None:
        super().__init__(db)

        self.table = 'settings'

        self.refresh()
