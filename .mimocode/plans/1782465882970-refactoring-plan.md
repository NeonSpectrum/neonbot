# NeonBot Refactoring Plan

## Goal

Restructure the entire NeonBot project from a `classes/` dumping ground into a clean domain-based architecture. Preserve all functionality, fix known bugs, simplify the codebase, and reduce file count from ~36 to ~27 Python files.

---

## Current Problems

1. `classes/` mixes AI, database, Discord UI, music, monitoring, voice events — no cohesion
2. Over-split tiny files: `enums/` (2 files, ~5 lines each), `dataclasses/` (1 file), `lavalink/` (2 files, ~10 lines each)
3. `event.py` (351 lines) handles unrelated events: lifecycle, AI chat, voice logging, presence tracking
4. File naming inconsistency: `views/` uses PascalCase
5. Duplicate `get_current_info()` in `exchange_gift.py` (second shadows first)
6. Dead code: unused `ThreadPoolExecutor` in `google.py`
7. Hardcoded guild/role IDs in `context_menu.py`
8. Dual env loading: both `dotenv` and `envparse` (redundant)
9. AGENTS.md references files that don't exist (`spotify.py`, `ytdl.py`, `chatgpt/`)

---

## New Directory Structure

```
neonbot/
├── __init__.py                  # Unchanged (exports NeonBot)
├── bot.py                       # Slimmed down (move voice events logic out)
├── env.py                       # Add CONTEXT_MENU_GUILD_ID, CONTEXT_MENU_GUEST_ROLE_ID, CONTEXT_MENU_MEMBER_ROLE_ID
│
├── core/                        # Bot infrastructure
│   ├── __init__.py
│   ├── database.py              # ← classes/database.py (unchanged)
│   └── google_auth.py           # ← classes/google.py (remove dead ThreadPoolExecutor code)
│
├── music/                       # Music subsystem (self-contained)
│   ├── __init__.py
│   ├── player.py                # ← classes/player/player.py (unchanged)
│   ├── player_controls.py       # ← classes/player/player_controls.py (update imports)
│   ├── player_message.py        # ← classes/player/player_message_manager.py (rename)
│   ├── ytmusic.py               # ← classes/player/ytmusic.py (update imports)
│   ├── lavalink_client.py       # ← classes/lavalink/client.py + player_manager.py (merge 2 tiny files)
│   └── voice_events.py          # ← classes/voice_events.py (unchanged)
│
├── ai/                          # AI integrations
│   ├── __init__.py
│   └── gemini.py                # ← classes/gemini.py (update imports)
│
├── features/                    # Standalone features
│   ├── __init__.py
│   ├── exchange_gift.py         # ← classes/exchange_gift.py (fix duplicate method, keep i18n version)
│   ├── exchange_gift_views.py   # ← views/ExchangeGiftView.py + WishlistModal.py + WishlistView.py (merge 3 → 1)
│   └── panel.py                 # ← classes/panel.py (update imports)
│
├── cogs/                        # Slash commands (unchanged files, update imports)
│   ├── administration.py
│   ├── event.py                 # Trimmed: only lifecycle (on_connect, on_ready, on_command, on_interaction, interaction_check, on_command_error, on_guild_join)
│   ├── exchange_gift.py
│   ├── lavalink_event.py
│   ├── music.py
│   ├── panel.py
│   ├── search.py
│   ├── updater.py
│   └── utility.py
│
├── models/                      # Database models (unchanged structure)
│   ├── __init__.py              # NEW: re-exports all models for convenience
│   ├── guild.py
│   ├── setting.py
│   ├── migration.py
│   ├── channel_log.py
│   ├── exchange_gift.py
│   ├── music.py
│   └── panel.py
│
├── discord_ui/                  # Reusable Discord UI components (renamed from classes/discord_utils/)
│   ├── __init__.py
│   ├── decorators.py            # ← classes/discord_utils/decorators.py (unchanged)
│   ├── embed.py                 # ← classes/discord_utils/embed.py (unchanged)
│   ├── select_choices.py        # ← classes/discord_utils/select_choices.py (unchanged)
│   └── view.py                  # ← classes/discord_utils/view.py (unchanged)
│
├── utils/                       # Shared utilities
│   ├── __init__.py              # Creates log singleton (unchanged)
│   ├── log.py                   # ← utils/log.py (unchanged)
│   ├── constants.py             # ← utils/constants.py (unchanged)
│   ├── functions.py             # ← utils/functions.py (unchanged)
│   ├── decorators.py            # ← merged INTO from classes/discord_utils/decorators.py → discord_ui/decorators.py
│   ├── context_menu.py          # ← utils/context_menu.py (use env vars instead of hardcoded IDs)
│   └── exceptions.py            # ← utils/exceptions.py (unchanged)
│
├── lang/                        # i18n JSON files (unchanged)
├── migrations/                  # DB migrations (unchanged)
├── assets/                      # Static data (unchanged)
├── dataclasses/                 # REMOVED → merged into models/__init__.py or kept inline
│   └── (merged: PlayerMessage → music/player.py or models/__init__.py)
└── enums/                       # REMOVED → merged into music/player.py
    └── (merged: MessageType, Repeat → music/player.py)
```

**Note**: `dataclasses/` and `enums/` directories are deleted. Their contents (PlayerMessage, MessageType, Repeat) are moved into `music/player.py` since they're only used by the music subsystem.

---

## File Mapping (Current → New)

| Current Path | New Path | Changes |
|---|---|---|
| `neonbot/__init__.py` | `neonbot/__init__.py` | Unchanged |
| `neonbot/bot.py` | `neonbot/bot.py` | Update imports |
| `neonbot/env.py` | `neonbot/env.py` | Add 3 context menu env vars |
| `main.py` | `main.py` | Remove `dotenv` import, remove `env.read_envfile()` |
| `classes/database.py` | `core/database.py` | Update imports |
| `classes/google.py` | `core/google_auth.py` | Remove unused ThreadPoolExecutor, remove unused `loop` var |
| `classes/player/player.py` | `music/player.py` | Inline MessageType, Repeat, PlayerMessage |
| `classes/player/player_controls.py` | `music/player_controls.py` | Update imports |
| `classes/player/player_message_manager.py` | `music/player_message.py` | Update imports |
| `classes/player/ytmusic.py` | `music/ytmusic.py` | Update imports |
| `classes/lavalink/client.py` | `music/lavalink_client.py` | Merge player_manager.py into this file |
| `classes/lavalink/player_manager.py` | (merged into lavalink_client.py) | Delete |
| `classes/voice_events.py` | `music/voice_events.py` | Unchanged |
| `classes/gemini.py` | `ai/gemini.py` | Update imports |
| `classes/exchange_gift.py` | `features/exchange_gift.py` | Remove duplicate `get_current_info()`, keep i18n version |
| `views/ExchangeGiftView.py` | `features/exchange_gift_views.py` | Merge all 3 views into 1 file |
| `views/WishlistModal.py` | (merged into exchange_gift_views.py) | Delete |
| `views/WishlistView.py` | (merged into exchange_gift_views.py) | Delete |
| `classes/panel.py` | `features/panel.py` | Update imports |
| `classes/discord_utils/decorators.py` | `discord_ui/decorators.py` | Unchanged |
| `classes/discord_utils/embed.py` | `discord_ui/embed.py` | Unchanged |
| `classes/discord_utils/select_choices.py` | `discord_ui/select_choices.py` | Unchanged |
| `classes/discord_utils/view.py` | `discord_ui/view.py` | Unchanged |
| `dataclasses/__init__.py` | (deleted) | Merge PlayerMessage into music/player.py |
| `dataclasses/player_message.py` | (deleted) | Merge into music/player.py |
| `enums/__init__.py` | (deleted) | Merge into music/player.py |
| `enums/message_type.py` | (deleted) | Merge into music/player.py |
| `enums/repeat.py` | (deleted) | Merge into music/player.py |
| `utils/__init__.py` | `utils/__init__.py` | Unchanged |
| `utils/log.py` | `utils/log.py` | Unchanged |
| `utils/constants.py` | `utils/constants.py` | Unchanged |
| `utils/functions.py` | `utils/functions.py` | Unchanged |
| `utils/context_menu.py` | `utils/context_menu.py` | Use env vars for guild/role IDs |
| `utils/exceptions.py` | `utils/exceptions.py` | Unchanged |
| `cogs/event.py` | `cogs/event.py` | Extract on_presence_update, on_voice_state_update, on_message AI chat |
| `cogs/event.py` (voice parts) | `cogs/music.py` | Add voice_state_update listener |
| `cogs/event.py` (AI chat) | `cogs/utility.py` | Move on_message Gemini chat logic here |
| `cogs/event.py` (presence) | `cogs/event.py` | Keep but simplified |

---

## Bug Fixes During Refactoring

1. **Duplicate `get_current_info()`** in `features/exchange_gift.py`: Remove lines 131-138 (hardcoded English), keep lines 122-129 (i18n)
2. **Dead code in `core/google_auth.py`**: Remove unused `concurrent.futures` import and `ThreadPoolExecutor` context managers (lines 25, 28), remove unused `loop` variable (line 22)
3. **Operator precedence bug** in `event.py` lines 309-316: Add parentheses to fix `and`/`or` precedence:
   ```python
   if (not after_activity and before_activity and before_activity.name == 'Custom Status') \
       or (not before_activity and after_activity and after_activity.name == 'Custom Status'):
   ```
4. **Hardcoded IDs** in `context_menu.py`: Replace with env vars `CONTEXT_MENU_GUILD_ID`, `CONTEXT_MENU_GUEST_ROLE_ID`, `CONTEXT_MENU_MEMBER_ROLE_ID`
5. **Dual env loading** in `main.py`: Remove `from dotenv import load_dotenv` and `load_dotenv()` call; `envparse` handles `.env` files already
6. **Duplicate `TYPE_CHECKING` import** in `player_message_manager.py`: Remove duplicate

---

## Additional Improvements

### 1. Create `models/__init__.py` with re-exports
```python
from .guild import GuildModel
from .setting import SettingModel
from .migration import MigrationModel
from .channel_log import ChannelLogModel
from .exchange_gift import ExchangeGiftModel, ExchangeGiftMember
from .music import MusicModel
from .panel import PanelModel, PanelServer
```
This allows `from neonbot.models import GuildModel` instead of `from neonbot.models.guild import GuildModel`.

### 2. Slim down `event.py` (351 → ~150 lines)
**Move out:**
- `on_voice_state_update` → `cogs/music.py` as a listener
- `on_presence_update` → stays in `event.py` but simplified
- `on_message` AI chat handling → `cogs/utility.py` (the Gemini chat logic)

**Keep in `event.py`:**
- `on_connect`, `on_disconnect`, `on_ready`
- `on_command`, `on_interaction`, `interaction_check`
- `on_command_error`, `on_guild_join`
- `on_node_connected` (from lavalink_event.py merge)
- `on_presence_update` (simplified)

### 3. Merge `lavalink_event.py` into `cogs/event.py`
The lavalink event cog is only 66 lines with simple listeners. Merge into `event.py` since it's bot lifecycle.

### 4. Update `AGENTS.md`
Remove references to non-existent files (`spotify.py`, `ytdl.py`, `chatgpt/`). Update structure section to match new layout.

---

## Implementation Order

### Phase 1: Create new directory structure
1. Create directories: `core/`, `music/`, `ai/`, `features/`, `discord_ui/`
2. Create `__init__.py` files in each

### Phase 2: Move and merge files (bottom-up, no import changes yet)
1. Move `classes/database.py` → `core/database.py`
2. Move `classes/google.py` → `core/google_auth.py` (fix dead code)
3. Move `classes/lavalink/client.py` → `music/lavalink_client.py` (merge player_manager.py)
4. Move `classes/player/player.py` → `music/player.py` (inline enums/dataclasses)
5. Move `classes/player/player_controls.py` → `music/player_controls.py`
6. Move `classes/player/player_message_manager.py` → `music/player_message.py`
7. Move `classes/player/ytmusic.py` → `music/ytmusic.py`
8. Move `classes/voice_events.py` → `music/voice_events.py`
9. Move `classes/gemini.py` → `ai/gemini.py`
10. Move `classes/exchange_gift.py` → `features/exchange_gift.py` (fix duplicate)
11. Merge `views/*.py` → `features/exchange_gift_views.py`
12. Move `classes/panel.py` → `features/panel.py`
13. Move `classes/discord_utils/*` → `discord_ui/`
14. Create `models/__init__.py` with re-exports

### Phase 3: Update all imports
Update every file that imports from old paths. Key files:
- `bot.py`: imports from `core/`, `discord_ui/`, `features/`
- `cogs/*.py`: imports from `music/`, `ai/`, `features/`, `discord_ui/`
- `music/*.py`: internal imports
- `ai/gemini.py`: imports from `discord_ui/`, `models/`

### Phase 4: Restructure event.py
1. Extract `on_voice_state_update` → add as listener in `cogs/music.py`
2. Extract `on_message` AI chat → add in `cogs/utility.py`
3. Merge `lavalink_event.py` into `event.py`
4. Fix operator precedence bug in `on_presence_update`

### Phase 5: Fix remaining bugs
1. Fix `main.py` (remove dotenv)
2. Fix `env.py` (add context menu vars)
3. Fix `utils/context_menu.py` (use env vars)
4. Remove dead code in `google_auth.py`

### Phase 6: Clean up
1. Delete old directories: `classes/`, `views/`, `dataclasses/`, `enums/`
2. Update `AGENTS.md`
3. Run `ruff check neonbot/` and `ruff format neonbot/`

---

## Verification

1. **Lint**: `ruff check neonbot/ && ruff format --check neonbot/`
2. **Import check**: `python -c "from neonbot import NeonBot"` (verifies all imports resolve)
3. **Start bot**: `bin/neonbot start` and verify it connects, loads cogs, and responds to commands
4. **Smoke test commands**: Test `/play`, `/chat`, `/exchangegift start`, `/panel startmonitor`
5. **Verify no old imports remain**: `grep -r "neonbot.classes" neonbot/` should return 0 results
6. **Verify no old view imports**: `grep -r "neonbot.views" neonbot/` should return 0 results
7. **Verify no old enum/dataclass imports**: `grep -r "neonbot.enums\|neonbot.dataclasses" neonbot/` should return 0 results
