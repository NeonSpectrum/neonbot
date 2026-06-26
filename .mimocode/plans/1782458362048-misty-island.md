# NeonBot Optimization & Bug Fix Plan

## Summary

Comprehensive audit found **35+ bugs** across the codebase. This plan organizes them into 8 work phases ordered by severity. Critical crash bugs and data-loss bugs are fixed first, then logic bugs, then code quality improvements.

---

## Phase 1: Critical Crash Bugs

### 1a. `compose.yml` — Duplicate `volumes` key (lines 4-11)
The `volumes` key appears twice under the `app` service. YAML silently overwrites the first (source mount `./:/app`) with the second (timezone mounts). The source code is never mounted.
**Fix:** Merge both volume lists into a single `volumes` key.

### 1b. `neonbot/models/guild.py:41` — `get_instance` raises KeyError
`guilds[guild_id]` raises `KeyError` for uncached guilds instead of returning `None`. This crashes every command if a guild isn't cached yet.
**Fix:** Use `guilds.get(guild_id)` to return `None` as the type hint promises.

### 1c. `neonbot/classes/player/player.py:372` — `voice_client.destroy()` after disconnect
`reset()` calls `disconnect(force=True, destroy=False)` which sets `self.voice_client = None` (line 178), then line 372 calls `self.voice_client.destroy()` — guaranteed `AttributeError`.
**Fix:** Save reference before disconnect, or skip destroy when voice_client is None.

### 1d. `neonbot/classes/chatgpt/chat_thread.py:11` — `MAX_TOKEN` is a string
`OPENAI_MAX_TOKEN` is loaded as `str` from env (no cast in env.py:42). The comparison `self.chat.token > ChatThread.MAX_TOKEN` (line 34) compares int to string → `TypeError` in Python 3.
**Fix:** Cast `OPENAI_MAX_TOKEN` to `int` in env.py with a default.

### 1e. `neonbot/cogs/search.py:154` — `data.message` on a dict
`data` is `await res.json()` (a dict), but line 154 uses `data.message` → `AttributeError`.
**Fix:** Change to `data['message']`.

### 1f. `neonbot/cogs/event.py:89-92` — Nested list passed to `files=`
`files=[[discord.File(...)] + gemini_chat.get_response_attachments()]` creates a nested list. Discord.py expects a flat list.
**Fix:** Remove the outer list brackets.

### 1g. `neonbot/env.py:8-10,17-21,53-62` — Missing defaults crash on import
`env.str('DISCORD_LOG_LEVEL')` etc. with no default raises `KeyError` if the env var is missing.
**Fix:** Add sensible defaults: `DISCORD_LOG_LEVEL='INFO'`, `BOT_LOG_LEVEL='INFO'`, `DEFAULT_PREFIX='.'`. For MONGO vars, add defaults matching the Docker compose setup.

---

## Phase 2: Logic Bugs in Player

### 2a. `neonbot/classes/player/player.py:405-408` — `find_new_current_queue` always returns 0
```python
if track.extra.get('index') == track_list[index].extra['index']:
```
`track` IS `track_list[index]`, so this is always true. Should compare against the currently-playing track's original index.
**Fix:** Compare against `self.current.extra['index']` (the original index of the track that was playing).

### 2b. `neonbot/classes/player/player.py:233-239` — `remove` shadows `index` parameter
The loop `for index, track in enumerate(...)` shadows the function parameter `index`, so the comparison `track.extra.get('index') > index` uses the loop counter instead of the removed track's index.
**Fix:** Rename the loop variable to `i` or `idx`, and compare against the removed track's original index (save it before popping).

### 2c. `neonbot/classes/player/player.py:419` — `wait_until` with no timeout
`await wait_until(lambda: self.is_playing)` has no timeout. If `is_playing` never becomes true, this blocks forever inside `_track_event_lock`.
**Fix:** Add a timeout parameter: `await wait_until(lambda: self.is_playing, timeout=30)`.

### 2d. `neonbot/classes/player/player.py:168` — `connect` assumes voice state
`self.ctx.author.voice.channel` will crash if the author is not in a voice channel.
**Fix:** Add a null check on `self.ctx.author.voice`.

---

## Phase 3: Null Safety & AttributeError Fixes

### 3a. `neonbot/classes/player/player_message_manager.py:53,63` — `get_user` returns None
`self.bot.get_user(track.requester).display_name` crashes if user is not cached.
**Fix:** Add fallback: `user = self.bot.get_user(track.requester); user.display_name if user else 'Unknown'`.

### 3b. `neonbot/classes/player/player_message_manager.py:88-91` — `replace_to_finished_playing` receives None
`get_latest_message()` can return `None`, then `player_message.track` crashes.
**Fix:** Add `if player_message is None: return` guard.

### 3c. `neonbot/classes/gemini.py:92` — `response.candidates[0]` without null check
If Gemini's safety filter blocks the response, `candidates` is empty or None.
**Fix:** Add guard: `if not response.candidates: raise error / return`.

### 3d. `neonbot/classes/gemini.py:149-152` — `get_command` returns None
`self.bot.get_command(row.get('name'))` can return None, then `command.callback` crashes.
**Fix:** Add `if not command: continue`.

### 3e. `neonbot/classes/gemini.py:197-198` — `get_user` returns None for owner
`self.bot.get_user(self.bot.app_info.owner.id).id` crashes if user not cached.
**Fix:** Use `self.bot.app_info.owner.id` directly (it's already an int).

### 3f. `neonbot/classes/player/ytmusic.py:46` — `results[0]` IndexError on empty
If YTMusic search returns no results, `results[0]` crashes.
**Fix:** Add `if not results: return None`.

### 3g. `neonbot/classes/player/ytmusic.py:71,91` — `counterpart` can be None
`track.get('counterpart')['videoId']` crashes if counterpart is missing.
**Fix:** Add null check or use `.get('counterpart', {}).get('videoId')`.

### 3h. `neonbot/views/ExchangeGiftView.py:66-68` — `get_member` returns None
`interaction.guild.get_member(member.user_id).mention` crashes if member left.
**Fix:** Add null check, skip or show "Unknown User".

---

## Phase 4: Enum & Type Fixes

### 4a. `neonbot/enums/repeat.py:9-10` — Broken `__eq__`
`Repeat.OFF == 0` is True but `0 == Repeat.OFF` is False. Asymmetric equality.
**Fix:** Remove the custom `__eq__` override. Use `Repeat(value)` for comparison or compare `.value`.

### 4b. `neonbot/enums/message_type.py:8-9` — Same broken `__eq__`
**Fix:** Same as 4a.

### 4c. `neonbot/env.py:42` — `OPENAI_MAX_TOKEN` not cast to int
Already addressed in Phase 1d. Ensure `int` cast with default like `4096`.

### 4d. `neonbot/env.py:14` — `DISABLED_COGS` uses `env.str` with list default
Should use `env.list()` instead.
**Fix:** Change to `env.list('DISABLED_COGS', default=[])`.

---

## Phase 5: Cog Fixes

### 5a. `neonbot/cogs/event.py:357-362` — Two Event instances created
`setup()` creates `cog` for method assignment, then creates a second instance via `add_cog(Event(bot))`.
**Fix:** Use the same instance: `await bot.add_cog(cog)`.

### 5b. `neonbot/cogs/event.py:193` — `raise error` after handling
Re-raises after sending user-facing message, causing duplicate error logging.
**Fix:** Remove the `raise error` line.

### 5c. `neonbot/cogs/event.py:104` — Nested quote f-string
`f'{self.bot.default_prefix}{command.name} {' '.join(args)}'` — SyntaxWarning on Python 3.10/3.11.
**Fix:** Use a variable for the joined args.

### 5d. `neonbot/cogs/administration.py:235,248,261` — Copy-pasted docstrings
All three say "Sets the chatgpt channel".
**Fix:** Correct each docstring.

### 5e. `neonbot/cogs/administration.py:243` — Nested quote f-string
Same issue as 5c.

### 5f. `neonbot/cogs/search.py:251` — Bare `except:`
Catches `SystemExit`, `KeyboardInterrupt`.
**Fix:** Change to `except Exception:`.

### 5g. `neonbot/cogs/panel.py:65` — `get_channel` returns None
`interaction.client.get_channel(panel.channel_id).fetch_message(...)` crashes if channel is deleted.
**Fix:** Add null check.

### 5h. `neonbot/cogs/panel.py:74-100` — Autocomplete hits API every keystroke
No caching for Panel server list.
**Fix:** Add a simple TTL cache (e.g., `cachetools.TTLCache` or manual timestamp check).

### 5i. `neonbot/cogs/updater.py:64` — `rstrip('.py')` strips chars not substring
`'file.py'.rstrip('.py')` strips individual chars `p`, `y`, `.`.
**Fix:** Use `.removesuffix('.py')` (Python 3.9+).

### 5j. `neonbot/cogs/updater.py:136-137` — Player reload updates wrong object
`player = interaction.client.lavalink.bot` then `player.__dict__.update(new_player)` — updates the bot, not the player.
**Fix:** Use the player manager to create the player instance and update it.

---

## Phase 6: Panel & Security Fixes

### 6a. `neonbot/classes/panel.py:42,60,78` — `ssl=False`
Disabled SSL on all API calls.
**Fix:** Remove `ssl=False` (defaults to True). If self-signed certs are needed, configure `ssl=True` with a custom SSL context.

### 6b. `neonbot/classes/panel.py:105-107` — `return` instead of `continue`
First server error skips all remaining servers.
**Fix:** Change `return` to `continue`.

### 6c. `neonbot/classes/panel.py:170` — Shadowed `server` variable
Reassigns the loop variable.
**Fix:** Use a different variable name like `guild_model`.

---

## Phase 7: Script & Config Fixes

### 7a. `bin/neonbot:1` — Missing `!` in shebang
`#/bin/bash` → `#!/bin/bash`.

### 7b. `bin/neonbot:24` — Uses pipenv instead of poetry
**Fix:** Change to `poetry update`.

### 7c. `bin/neonbot:30` — Incomplete usage string
**Fix:** List all valid commands.

### 7d. `start.sh:14` — Regex `'^neonbot/cog'` misses `cogs/`
**Fix:** Change to `'^neonbot/cogs'`.

### 7e. `neonbot/classes/chatgpt/chatgpt.py:46-57` — `chat_thread` unbound in finally
If `channel.edit(locked=True)` fails, `chat_thread` is never assigned.
**Fix:** Move the post-finally code into the try block, or initialize `chat_thread = None` and guard.

---

## Phase 8: Minor Code Quality

### 8a. `neonbot/utils/functions.py:23-30` — `shell_exec` discards stderr
**Fix:** Return both stdout and stderr, or log stderr.

### 8b. `neonbot/classes/player/player.py:265-268` — Two `if` instead of `if/elif`
**Fix:** Change second `if` to `elif`.

### 8c. `neonbot/cogs/lavalink_event.py:19` — `clear()` removes all hooks
**Fix:** Only remove the hooks this cog added.

### 8d. `neonbot/models/exchange_gift.py:16` — `Optional[bool]` for `finish`
**Fix:** Change to `bool` with default `False`.

### 8e. `neonbot/classes/exchange_gift.py:84-96` — Shuffle can deadlock on last iteration
When only one member remains who hasn't been chosen, `random.choice([])` raises `IndexError`.
**Fix:** Implement proper derangement algorithm or retry.

---

## Files to Modify

| File | Phases |
|------|--------|
| `compose.yml` | 1a |
| `neonbot/models/guild.py` | 1b |
| `neonbot/classes/player/player.py` | 1c, 2a, 2b, 2c, 2d, 8b |
| `neonbot/classes/chatgpt/chat_thread.py` | 1d |
| `neonbot/cogs/search.py` | 1e, 5f |
| `neonbot/cogs/event.py` | 1f, 5a, 5b, 5c |
| `neonbot/env.py` | 1g, 4c, 4d |
| `neonbot/classes/player/player_message_manager.py` | 3a, 3b |
| `neonbot/classes/gemini.py` | 3c, 3d, 3e |
| `neonbot/classes/player/ytmusic.py` | 3f, 3g |
| `neonbot/views/ExchangeGiftView.py` | 3h |
| `neonbot/enums/repeat.py` | 4a |
| `neonbot/enums/message_type.py` | 4b |
| `neonbot/cogs/administration.py` | 5d, 5e |
| `neonbot/cogs/panel.py` | 5g, 5h |
| `neonbot/cogs/updater.py` | 5i, 5j |
| `neonbot/classes/panel.py` | 6a, 6b, 6c |
| `bin/neonbot` | 7a, 7b, 7c |
| `start.sh` | 7d |
| `neonbot/classes/chatgpt/chatgpt.py` | 7e |
| `neonbot/utils/functions.py` | 8a |
| `neonbot/cogs/lavalink_event.py` | 8c |
| `neonbot/models/exchange_gift.py` | 8d |
| `neonbot/classes/exchange_gift.py` | 8e |

## Verification

1. Run `ruff check neonbot/` to verify no linting errors
2. Run `python -c "from neonbot.env import *"` to verify env loading
3. Run `python -c "from neonbot.enums import Repeat; assert Repeat.OFF == Repeat.OFF"` to verify enum fix
4. Run `docker compose config` to verify compose.yml is valid
5. Run `bash -n bin/neonbot` to verify shell script syntax
6. If bot can start: test music play/queue/shuffle/remove cycle, test Gemini mention, test panel monitor
