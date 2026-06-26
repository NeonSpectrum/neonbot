# Agent Instructions for NeonBot

## Project Overview

Discord bot (v2.3.0) built with discord.py, MongoDB (Beanie ODM), and Docker. Music player, AI chatbots (ChatGPT, Gemini), server management features.

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

## Running Locally (without Docker)

```bash
# Requires Python 3.9, ffmpeg, aria2, libopus
cp .env.example .env  # Fill in TOKEN and MONGO_URL
pip install -r requirements.txt
python main.py
```

## Environment Variables

Copy `.env.example` to `.env`. Required:
- `TOKEN` - Discord bot token
- `MONGO_URL` - MongoDB connection (default: `mongodb://mongo`)
- `MONGO_DB_NAME`, `MONGO_DB_USERNAME`, `MONGO_DB_PASSWORD`

Optional: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API`, `SPOTIFY_CLIENT_ID/SECRET`, etc.

## Code Structure

```
neonbot/
├── bot.py              # Bot class, setup, lifecycle
├── cogs/               # Command groups (slash commands)
│   ├── music.py        # Play, queue, playlist commands
│   ├── administration.py  # Server config, eval
│   ├── search.py       # Web search, dictionary, anime
│   ├── utility.py      # Misc tools
│   ├── event.py        # Event handlers (on_message, errors)
│   ├── panel.py        # Server management panel
│   └── exchange_gift.py # Gift exchange feature
├── classes/            # Business logic
│   ├── player.py       # Music player (per-guild singleton)
│   ├── ytdl.py         # YouTube download via yt-dlp
│   ├── chatgpt/        # OpenAI integration
│   ├── gemini.py       # Google Gemini integration
│   ├── spotify.py      # Spotify API
│   └── database.py     # MongoDB/Beanie init
├── models/             # Beanie document models
│   ├── guild.py        # Per-guild settings (cached in memory)
│   └── setting.py      # Global bot settings
├── utils/              # Helpers, constants, logging
├── lang/               # i18n JSON files
└── views/              # Discord UI views/modals
```

## Key Patterns

- **Slash commands only**: All commands use `@app_commands.command()` (no prefix commands except `eval`)
- **Singleton per guild**: `Player` and `Guild` use class-level `servers` dict with `get_instance(guild_id)`
- **Beanie ODM**: Models extend `Document`, use `find_one()`, `create()`, etc.
- **Cog auto-loading**: Files in `neonbot/cogs/` are auto-loaded alphabetically (skip files starting with `_`)
- **i18n**: Uses `python-i18n` with JSON files in `neonbot/lang/`
- **Env loading**: Both `dotenv` and `envparse` are used (redundant but established)

## Conventions

- 4-space indentation, no trailing newlines (`.editorconfig`)
- Type hints used throughout
- Async/await for all I/O
- Logging via custom `neonbot.utils.log` module
- Embeds via `neonbot.classes.embed.Embed` wrapper

## Gotchas

- `main.py` clears `debug.log` and `tmp/youtube_dl/` on startup
- `SYNC_COMMANDS=true` (default) syncs slash commands to all guilds on boot - can be slow with many guilds
- Player state cached to `tmp/players/` - set `LOAD_PLAYER_CACHE=true` to restore on restart
- `lib/libopus.so.0` is bundled for voice support
- No tests or CI configured
- `eval` command is owner-only and uses prefix command (not slash)
