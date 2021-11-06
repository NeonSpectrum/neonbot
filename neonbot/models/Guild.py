from motor.motor_asyncio import AsyncIOMotorClient as MotorClient

from .Model import Model


class Guild(Model):
    def __init__(self, db: MotorClient, guild_id: int) -> None:
        super().__init__(db)

        self.table = "servers"
        self.where = {"server_id": str(guild_id)}
