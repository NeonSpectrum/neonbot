# Agent Instructions for NeonBot

## Project Overview

Discord bot (v2.5.0) built with discord.py, MongoDB (Beanie ODM), and Docker. Music player, AI chatbots (Gemini), server management features.

## Quick Start

```bash
# Start bot + MongoDB
bin/neonbot start

# View logs
bin/neonbot logs

# Rebuild after dependency changes
bin/neonbot rebuild

# Access container shell
bin/neonbot bash
```

## Package Management (Poetry)

```bash
# Install dependencies
poetry install

# Add a dependency
poetry add <package>

# Run a command inside the venv
poetry run python main.py

# Check installed packages
poetry show

# Check a specific package
poetry show <package>
```

## Running Locally (without Docker)

```bash
# Requires Python 3.10+, ffmpeg, libopus
cp .env.example .env  # Fill in TOKEN and MONGO_URL
pip install -r requirements.txt
python main.py
```

## Environment Variables

Copy `.env.example` to `.env`. Required:
- `TOKEN` - Discord bot token
- `MONGO_URL` - MongoDB connection (default: `mongodb://mongo`)
- `MONGO_DB_NAME`, `MONGO_DB_USERNAME`, `MONGO_DB_PASSWORD`

Optional: `GEMINI_API_KEY`, `GOOGLE_API`, `SPOTIFY_CLIENT_ID/SECRET`, etc.

## Code Structure

```
neonbot/
├── bot.py              # NeonBot class, setup, lifecycle
├── env.py              # All environment variable parsing
├── core/               # Bot infrastructure
│   ├── database.py     # MongoDB/Beanie init + migrations
│   └── google_auth.py  # Google auth token helper
├── music/              # Music subsystem (self-contained)
│   ├── player.py       # Player(DefaultPlayer), queue, shuffle, autoplay
│   ├── player_controls.py  # Discord button controls
│   ├── player_message.py   # Now Playing message manager
│   ├── ytmusic.py      # YTMusic API integration
│   ├── lavalink_client.py  # Custom Lavalink Client + PlayerManager
│   ├── voice_events.py     # Voice state change handler
│   └── enums.py        # MessageType, Repeat, PlayerMessage
├── ai/                 # AI integrations
│   └── gemini.py       # Google Gemini integration
├── features/           # Standalone features
│   └── panel.py        # Pterodactyl panel monitoring
├── cogs/               # Command groups (slash commands)
│   ├── music.py        # Play, queue, playlist commands
│   ├── administration.py  # Server config, eval
│   ├── search.py       # Web search, weather
│   ├── utility.py      # Misc tools, chat, imagine
│   ├── event.py        # Event handlers (on_message, errors)
│   ├── panel.py        # Server management panel
│   └── updater.py      # Git pull + hot reload
├── discord_ui/         # Reusable Discord UI components
│   ├── embed.py        # Embed, PaginationEmbed, EmbedChoices
│   ├── view.py         # Button/View base classes
│   ├── decorators.py   # Command decorators (in_voice, has_permission, etc.)
│   └── select_choices.py  # SelectChoices UI component
├── models/             # Beanie document models
│   ├── __init__.py     # Re-exports all models
│   ├── guild.py        # Per-guild settings (cached in memory)
│   ├── setting.py      # Global bot settings
│   └── ...             # Embedded models (music, channel_log, etc.)
├── utils/              # Helpers, constants, logging
├── lang/               # i18n JSON files
├── migrations/         # Database migrations
└── assets/             # Static data (city.list.json, lang.json)
```

## Key Patterns

- **Slash commands only**: All commands use `@app_commands.command()` (no prefix commands except `eval`)
- **Singleton per guild**: `Player` and `GuildModel` use class-level dicts with `get_instance(guild_id)`
- **Beanie ODM**: Models extend `Document`, use `find_one()`, `create()`, etc.
- **Cog auto-loading**: Files in `neonbot/cogs/` are auto-loaded alphabetically (skip files starting with `_`)
- **i18n**: Uses `python-i18n` with JSON files in `neonbot/lang/`
- **Env loading**: Uses `envparse` for all environment variables

## Conventions

- 4-space indentation, no trailing newlines (`.editorconfig`)
- Type hints used throughout
- Async/await for all I/O
- Logging via custom `neonbot.utils.log` module
- Embeds via `neonbot.discord_ui.embed.Embed` wrapper
- **Commit messages**: Use format `<type>(<scope>): <description>` (e.g., `fix(music): resolve player crash on empty queue`)
- **Always run tests before committing**: `poetry run pytest tests/ -x -q`

## Gotchas

- `main.py` clears `debug.log` on startup
- `SYNC_COMMANDS=true` (default) syncs slash commands to all guilds on boot
- Player state cached to `tmp/players/` - set `LOAD_PLAYER_CACHE=true` to restore on restart
- `lib/libopus.so.0` is bundled for voice support
- `eval` command is owner-only and uses prefix command (not slash)

## References

- discord.py API docs: https://discordpy.readthedocs.io/en/stable/api.html
