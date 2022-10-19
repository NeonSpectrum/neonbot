from .model import Model


class Settings(Model):
    def __init__(self) -> None:
        super().__init__()

        self.table = "settings"

    async def create_default_collection(self):
        await self.refresh()

        if self.get() is None:
            await self.insert({
                "status": "online",
                "activity_type": "listening",
                "activity_name": "my heartbeat"
            })
