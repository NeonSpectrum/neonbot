from pymongo.asynchronous.database import AsyncDatabase


async def up(db: AsyncDatabase) -> None:
    await db.drop_collection('flyff')
