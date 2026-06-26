# NeonBot Optimization & Bug Fix Plan

## Overview
Comprehensive bug fixes and optimizations for the Discord bot. 26 issues identified across 4 priority tiers.

---

## Phase 1: Critical Runtime Bugs (6 fixes)

### 1.1 Fix `sync` command crash — `administration.py:228-229`
**Bug:** `asyncio` and `guilds` not imported; `self.bot(guild)` is meaningless.
**Fix:** Remove line 229 entirely. Line 228 (`bot.sync_command()`) already syncs commands globally.
```python
# Before
await bot.sync_command()
await asyncio.gather(*[self.bot(guild) for guild in guilds])

# After
await bot.sync_command()
```

### 1.2 Fix `set_status` attribute error — `administration.py:122`
**Bug:** `bot.settings.get('status')` references non-existent dict. Should be `bot.setting.status`.
```python
# Before
embed=Embed(f"Status is now set to {bot.settings.get('status')}."))

# After
embed=Embed(f"Status is now set to {bot.setting.status}."))
```

### 1.3 Fix `WishlistView.py` wrong import — `WishlistView.py:1`
**Bug:** `from ctypes import cast` imports C type casting, not Python typing.
```python
# Before
from ctypes import cast

# After
from typing import cast
```

### 1.4 Fix `Guild.get_instance` KeyError — `guild.py:41`
**Bug:** `guilds[guild_id]` raises KeyError; return type promises Optional[Guild].
```python
# Before
return guilds[guild_id]

# After
return guilds.get(guild_id)
```

### 1.5 Fix Gemini import-time crash — `gemini.py:11`
**Bug:** `genai.configure(api_key=env.str('GEMINI_API_KEY'))` runs at import time. Missing key crashes bot startup even if Gemini won't be used.
**Fix:** Defer configuration to first use via lazy init. API key remains required but won't crash import.
```python
# Before (module level)
genai.configure(api_key=env.str('GEMINI_API_KEY'))

# After
_gemini_configured = False

def _ensure_gemini():
    global _gemini_configured
    if not _gemini_configured:
        genai.configure(api_key=env.str('GEMINI_API_KEY'))
        _gemini_configured = True

# In GeminiChat.__init__:
    def __init__(self, message):
        _ensure_gemini()
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        ...
```

### 1.6 Fix Panel import-time crash — `panel.py:22-23`
**Bug:** `env.str('PANEL_URL')` and `env.str('PANEL_API_KEY')` run at class definition time, crashing import if env vars not set.
**Fix:** Defer to first use via class method.
```python
# Before
class Panel:
    URL = env.str('PANEL_URL')
    API_KEY = env.str('PANEL_API_KEY')

# After
class Panel:
    URL = None
    API_KEY = None

    @classmethod
    def _ensure_config(cls):
        if cls.URL is None:
            cls.URL = env.str('PANEL_URL')
            cls.API_KEY = env.str('PANEL_API_KEY')
```
Call `Panel._ensure_config()` at the top of each public method.

---

## Phase 2: High-Priority Logic Bugs (6 fixes)

### 2.1 Fix save_cache mutating live queue — `player.py:540-562`
**Bug:** `map_queue` modifies track dicts in-place, replacing `requested` User objects with IDs. After save, embed rendering crashes (`display_avatar` on int).
**Fix:** Deep copy the queue before serialization.
```python
# Before (inside save_cache)
json.dump({
    'queue': list(map(map_queue, self.queue)),
    ...
}, f, indent=4)

# After
import copy
queue_copy = copy.deepcopy(self.queue)
for track in queue_copy:
    if hasattr(track['requested'], 'id'):
        track['requested'] = track['requested'].id
    track['stream'] = None
json.dump({
    'queue': queue_copy,
    ...
}, f, indent=4)
```
Remove the old `map_queue` function inside save_cache.

### 2.2 Fix `reconnect` command — `music.py:267-276`
**Bug:** Disconnects then calls `play()`, but `play()` returns immediately without a connection.
**Fix:** Add `connect()` call before `play()`.
```python
# Before
await player.disconnect(force=True)
await player.play()

# After
await player.disconnect(force=True)
await player.connect()
await player.play()
```

### 2.3 Fix `deletemonitor` not persisting — `panel.py:60-65`
**Bug:** Sets `server.panel.servers[server_id] = PanelServer()` but never saves to DB.
**Fix:** Add `await server.save_changes()` after the deletion.
```python
# After line 60
server.panel.servers[server_id] = PanelServer()
await server.save_changes()  # Add this line
```

### 2.4 Fix `remove_song` negative index — `player.py:361-367`
**Bug:** When `current_track` is 0 and current song is removed, `current_track -= 1` becomes -1.
**Fix:** Add bounds check.
```python
# Before
if self.track_list[self.current_track] == index:
    self.current_track -= 1
    self.state = PlayerState.REMOVED
    self.next()

# After
if self.track_list[self.current_track] == index:
    if self.current_track > 0:
        self.current_track -= 1
    self.state = PlayerState.REMOVED
    self.next()
```

### 2.5 Fix `after()` error handling — `player.py:276-279`
**Bug:** FFmpeg error causes player to stall silently (zombie player).
**Fix:** On error, attempt to play next track or reset player.
```python
# Before
async def after(self, error=None):
    if error:
        log.error(error)
        return

# After
async def after(self, error=None):
    if error:
        log.error(error)
        if self.state != PlayerState.NONE and self.state != PlayerState.STOPPED:
            self.loop.create_task(self.after())
        return
```

### 2.6 Fix `start_monitor` variable shadowing — `panel.py:90-96`
**Bug:** Loop variable `panel` (PanelServer) is overwritten by `panel = Panel(server_id)`.
**Fix:** Rename the local variable.
```python
# Before
for server_id, panel in server.panel.servers.items():
    ...
    panel = Panel(server_id)

# After
for server_id, panel_config in server.panel.servers.items():
    ...
    panel_client = Panel(server_id)
```
Then update all references in the loop to use `panel_client`.

---

## Phase 3: Medium-Priority Fixes (8 fixes)

### 3.1 Remove dead code — `administration.py:113`
**Bug:** `if status is False` is dead code (discord.Status is never False).
**Fix:** Remove lines 113-114.

### 3.2 Fix Gemini None response — `event.py:84`
**Bug:** `len(response)` crashes if `get_response()` returns None.
```python
# Before
if len(response) > 2000:

# After
if response and len(response) > 2000:
```

### 3.3 Fix `debug.log` file handle leak — `main.py:25`
```python
# Before
open('./debug.log', 'w').close()

# After
with open('./debug.log', 'w') as f:
    pass
```

### 3.4 Fix bare except in ytdl — `ytdl.py:68-69`
```python
# Before
except:
    raise YtdlError()

# After
except Exception:
    raise YtdlError()
```

### 3.5 Fix deprecated `get_event_loop` — `bot.py:34`
```python
# Before
self.loop = asyncio.get_event_loop()

# After
self.loop = asyncio.new_event_loop()
asyncio.set_event_loop(self.loop)
```

### 3.6 Fix Repeat enum comparison — `repeat.py:9-10`
**Bug:** Custom `__eq__` breaks `Repeat.OFF == Repeat.OFF` (returns False).
**Fix:** Make `__eq__` handle both int and Enum comparisons.
```python
# Before
def __eq__(self, other):
    return self.value == other

# After
def __eq__(self, other):
    if isinstance(other, Repeat):
        return self is other
    return self.value == other
```

### 3.7 Fix panel `add_minecraft` silent error — `panel.py:196-197`
```python
# Before
except (ContentTypeError, asyncio.TimeoutError) as error:
    pass

# After
except (ContentTypeError, asyncio.TimeoutError) as error:
    log.warn(f'Minecraft status fetch failed: {error}')
```

### 3.8 Fix ThreadPoolExecutor max_workers — `bot.py:35`
```python
# Before
self.thread_pool = ThreadPoolExecutor()

# After
self.thread_pool = ThreadPoolExecutor(max_workers=16)
```

---

## Phase 4: Low-Priority Optimizations (3 fixes)

### 4.1 Consolidate env loading — `main.py:9-10`
Remove redundant `load_dotenv()` since `env.read_envfile()` already loads `.env`.
```python
# Before
from dotenv import load_dotenv
load_dotenv()
env.read_envfile()

# After
env.read_envfile()
```
Remove `from dotenv import load_dotenv`.

### 4.2 Fix guild cache leak — `guild.py`
Add cleanup in `on_guild_remove` handler in `event.py`:
```python
# In event.py, add handler
@staticmethod
@bot.event
async def on_guild_remove(guild):
    from neonbot.models.guild import guilds
    guilds.pop(guild.id, None)
    player = Player.get_instance_from_guild(guild)
    if player:
        player.remove_instance()
```

### 4.3 Add Player creation lock — `player.py:60-68`
Prevent race condition when two interactions create a Player simultaneously.
```python
# Add class-level lock
_servers_lock = asyncio.Lock()

@staticmethod
async def get_instance(origin) -> Player:
    guild_id = origin.guild.id
    async with Player._servers_lock:
        if guild_id not in Player.servers:
            ctx = await bot.get_context(origin)
            Player.servers[guild_id] = Player(ctx)
    return Player.servers[guild_id]
```

---

## Files Modified
1. `neonbot/cogs/administration.py` — fixes 1.1, 1.2, 3.1
2. `neonbot/views/WishlistView.py` — fix 1.3
3. `neonbot/models/guild.py` — fix 1.4
4. `neonbot/classes/gemini.py` — fix 1.5
5. `neonbot/classes/panel.py` — fixes 1.6, 2.6, 3.7
6. `neonbot/classes/player.py` — fixes 2.1, 2.4, 2.5, 4.3
7. `neonbot/cogs/music.py` — fix 2.2
8. `neonbot/cogs/panel.py` — fix 2.3
9. `neonbot/cogs/event.py` — fixes 3.2, 4.2
10. `main.py` — fix 3.3, 4.1
11. `neonbot/classes/ytdl.py` — fix 3.4
12. `neonbot/bot.py` — fixes 3.5, 3.8
13. `neonbot/enums/repeat.py` — fix 3.6

## Verification
1. `python -m py_compile neonbot/cogs/administration.py` — syntax check
2. `python -m py_compile neonbot/classes/player.py` — syntax check
3. `python -m py_compile neonbot/classes/gemini.py` — syntax check
4. `python -m py_compile neonbot/classes/panel.py` — syntax check
5. `python -m py_compile neonbot/views/WishlistView.py` — syntax check
6. `python -m py_compile neonbot/enums/repeat.py` — syntax check
7. `python -c "from neonbot.models.guild import Guild; print(Guild.get_instance(0))"` — verify returns None
8. `python -c "from neonbot.enums.repeat import Repeat; assert Repeat.OFF == Repeat.OFF; assert Repeat.OFF == 0"` — verify enum
9. `python -c "from neonbot.classes.gemini import GeminiChat"` — verify import works without env var
10. Full bot startup: `python main.py` (requires .env with TOKEN, MONGO_URL, GEMINI_API_KEY, PANEL_URL, PANEL_API_KEY)
