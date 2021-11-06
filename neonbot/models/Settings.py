from motor.motor_asyncio import AsyncIOMotorClient as MotorClient

from .Model import Model


class Settings(Model):
    def __init__(self, db: MotorClient) -> None:
        super().__init__(db)

        self.table = 'settings'
