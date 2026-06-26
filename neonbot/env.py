from envparse import env

TZ = env.str('TZ', default='Asia/Manila')
TOKEN = env.str('TOKEN')
OWNER_GUILD_IDS = env.list('OWNER_GUILD_IDS', default=[], subcast=int)
OWNER_IDS = env.list('OWNER_IDS', default=[], subcast=int)

DISCORD_LOG_LEVEL = env.str('DISCORD_LOG_LEVEL', default='INFO')
BOT_LOG_LEVEL = env.str('BOT_LOG_LEVEL', default='INFO')
DEFAULT_PREFIX = env.str('DEFAULT_PREFIX', default='.')

SYNC_COMMANDS = env.bool('SYNC_COMMANDS', default=False)
PROXY = env.str('PROXY', default=None)
DISABLED_COGS = env.list('DISABLED_COGS', default=[])
ENABLE_AUTOJOIN = env.bool('ENABLE_AUTOJOIN', default=True)

MONGO_IP = env.str('MONGO_IP', default='mongo')
MONGO_DB_NAME = env.str('MONGO_DB_NAME', default='neonbot')
MONGO_DB_USERNAME = env.str('MONGO_DB_USERNAME', default='')
MONGO_DB_PASSWORD = env.str('MONGO_DB_PASSWORD', default='')
MONGO_DB_PORT = env.int('MONGO_DB_PORT', default=27017)

GOOGLE_API = env.str('GOOGLE_API', default=None)
GOOGLE_CX = env.str('GOOGLE_CX', default=None)

DICTIONARY_API = env.str('DICTIONARY_API', default=None)
PASTEBIN_API = env.str('PASTEBIN_API', default=None)
OPENWEATHERMAP_API = env.str('OPENWEATHERMAP_API', default=None)

SPOTIFY_CLIENT_ID = env.str('SPOTIFY_CLIENT_ID', default=None)
SPOTIFY_CLIENT_SECRET = env.str('SPOTIFY_CLIENT_SECRET', default=None)

GOOGLE_APPLICATION_CREDENTIALS = env.str('GOOGLE_APPLICATION_CREDENTIALS', default=None)
CLEVERBOT_API = env.str('CLEVERBOT_API', default=None)

SEMAPHONE_API_KEY = env.str('SEMAPHONE_API_KEY', default=None)
SEMAPHONE_SENDER_NAME = env.str('SEMAPHONE_SENDER_NAME', default=None)

PANEL_URL = env.str('PANEL_URL', default=None)
PANEL_API_KEY = env.str('PANEL_API_KEY', default=None)

GEMINI_API_KEY = env.str('GEMINI_API_KEY', default=None)
GEMINI_CHAT_MODEL = env.str('GEMINI_CHAT_MODEL', default=None)
GEMINI_IMAGE_MODEL = env.str('GEMINI_IMAGE_MODEL', default=None)

RAPID_API_KEY = env.str('RAPID_API_KEY', default=None)

LAVALINK_HOST = env.str('LAVALINK_HOST', default='lavalink')
LAVALINK_PORT = env.str('LAVALINK_PORT', default='2333')
LAVALINK_PASSWORD = env.str('LAVALINK_PASSWORD', default='youshallnotpass')

YTMUSIC_CREDENTIALS_TYPE = env.str('YTMUSIC_CREDENTIALS_TYPE', default='oauth')
YTMUSIC_CREDENTIALS_JSON = env.str('YTMUSIC_CREDENTIALS_JSON', default='')
YTMUSIC_BRAND_ACCOUNT_ID = env.str('YTMUSIC_BRAND_ACCOUNT_ID', default=None)
YTMUSIC_CLIENT_ID = env.str('YTMUSIC_CLIENT_ID', default='')
YTMUSIC_CLIENT_SECRET = env.str('YTMUSIC_CLIENT_SECRET', default='')
YTMUSIC_COUNTRY = env.str('YTMUSIC_COUNTRY', default='US')
