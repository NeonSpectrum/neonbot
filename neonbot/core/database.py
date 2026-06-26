from __future__ import annotations

import asyncio
import importlib
import re
from datetime import datetime, timezone
from pathlib import Path
from time import time
from typing import List, TYPE_CHECKING

import discord
from beanie import init_beanie
from beanie.odm.operators.find.comparison import In
from pymongo import AsyncMongoClient

from neonbot.env import MONGO_DB_HOST, MONGO_DB_NAME, MONGO_DB_USERNAME, MONGO_DB_PASSWORD, MONGO_DB_PORT
from neonbot.models.guild import GuildModel
from neonbot.models.migration import MigrationModel
from neonbot.models.setting import SettingModel
from neonbot.utils import log

if TYPE_CHECKING:
    from neonbot import NeonBot


class Database:
    def __init__(self, bot: 'NeonBot'):
        self.client = None
        self.bot = bot
        self.settings = None
        self.db = None

    async def initialize(self) -> Database:
        mongo_host = MONGO_DB_HOST
        db_name = MONGO_DB_NAME
        db_username = MONGO_DB_USERNAME
        db_password = MONGO_DB_PASSWORD
        db_port = MONGO_DB_PORT

        start_time = time()

        log.info('Connecting to Database...')
        client = AsyncMongoClient(host=mongo_host, port=db_port, username=db_username, password=db_password)
        self.db = client.get_database(db_name)
        await init_beanie(database=self.db, document_models=[GuildModel, SettingModel, MigrationModel])
        log.info(f'MongoDB connection established in {(time() - start_time):.2f}s')

        await SettingModel.initialize()

        return self

    async def run_migrations(self) -> None:
        migrations_dir = Path(__file__).resolve().parent.parent / 'migrations'

        if not migrations_dir.is_dir():
            log.info('No migrations directory found. Skipping.')
            return

        pattern = re.compile(r'^(\d+)_.*\.py$')
        files = sorted(
            [f for f in migrations_dir.iterdir() if pattern.match(f.name)],
            key=lambda f: f.name,
        )

        if not files:
            return

        applied = {
            doc.name
            async for doc in MigrationModel.find_all()
        }

        pending = [f for f in files if f.stem not in applied]

        if not pending:
            log.info('All migrations already applied.')
            return

        log.info(f'Running {len(pending)} pending migration(s)...')

        for migration_file in pending:
            module_name = f'neonbot.migrations.{migration_file.stem}'
            module = importlib.import_module(module_name)

            log.info(f'Applying migration: {migration_file.stem}')
            await module.up(self.db)
            await MigrationModel(
                name=migration_file.stem,
                applied_at=datetime.now(timezone.utc),
            ).create()
            log.info(f'Migration applied: {migration_file.stem}')

        log.info(f'All {len(pending)} migration(s) applied successfully.')

    async def get_guilds(self, guilds: List[discord.Guild]) -> None:
        guild_ids = [guild.id for guild in guilds]
        existing_guild_ids = [server.id for server in await GuildModel.find(In(GuildModel.id, guild_ids)).to_list()]
        new_guild = [guild for guild in guilds if guild.id not in existing_guild_ids]

        for guild in new_guild:
            log.info(f'Creating database for {guild}...')
            await GuildModel.create_default_collection(guild.id)

        await asyncio.gather(*[self.cache_guild(guild) for guild in guilds])

    async def cache_guild(self, guild):
        log.info(f'Caching guild settings: {guild} ({guild.id})')
        await GuildModel.create_instance(guild.id)
