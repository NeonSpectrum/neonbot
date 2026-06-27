from pymongo.asynchronous.database import AsyncDatabase


async def up(db: AsyncDatabase) -> None:
    await db['guilds'].update_many(
        {},
        {'$unset': {'exchange_gift': ''}}
    )
