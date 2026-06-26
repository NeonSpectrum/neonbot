# Database Migration System

## Files to Create

### 1. `neonbot/models/migration.py` — MigrationModel (Beanie Document)
- Fields: `name: str`, `applied_at: datetime`
- Collection: `migrations`
- Registered in `init_beanie` alongside `GuildModel` and `SettingModel`

### 2. `neonbot/migrations/__init__.py` — Empty package init

### 3. `neonbot/migrations/001_remove_flyff.py` — Drops the flyff collection
- Calls `await db.drop_collection('flyff')` to clean up leftover data from the removed flyff feature
- Renames existing `001_sample_migration.py` → `001_remove_flyff.py`

## Files to Modify

### 4. `neonbot/classes/database.py`
- Add `MigrationModel` to `init_beanie(document_models=[...])` (line 41)
- Add `run_migrations()` method that:
  - Scans `neonbot/migrations/` for `^(\d+)_.*\.py$` files, sorted by name
  - Queries `MigrationModel` for already-applied migration names
  - For each pending: `importlib.import_module()`, `await module.up(self.db)`, create `MigrationModel` record
  - Logs progress
- Delete the existing `start_migration()` stub (lines 64-71)

### 5. `neonbot/bot.py` — `setup_hook()`
- Add `await self.db.run_migrations()` right after `await self.db.initialize()` (line 82)
- Remove `await self.db.start_migration(guilds)` call (line 102)

## Migration File Convention
- Location: `neonbot/migrations/`
- Naming: `{NNN}_{description}.py` (e.g., `001_add_premium_field.py`)
- Interface: `async def up(db: AsyncDatabase) -> None`
- `db` is the raw pymongo `AsyncDatabase` — access collections via `db.guilds`, `db.settings`, etc.
- No rollback support (`down()`) — matches project simplicity

## Execution Order in setup_hook
```
db.initialize()          → MongoDB connect, init_beanie (registers MigrationModel)
db.run_migrations()      → Scan, compare, apply pending migrations
SettingModel.get_instance()
... (presence, session, scheduler, lavalink, cogs, sync)
db.get_guilds(guilds)    → Schema already migrated before guild caching
```

## Verification
1. Start bot → `migrations` collection created in MongoDB
2. First run → log shows "Running 1 pending migration(s)...", `flyff` collection dropped, record in `migrations` collection
3. Restart → log shows "All migrations already applied.", no duplicates
4. Add `002_test.py` → verify it runs after `001`
5. Failed migration → bot doesn't start, failure not recorded
