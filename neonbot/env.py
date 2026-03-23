from envparse import env

TZ = env.str('TZ', default='Asia/Manila')
TOKEN = env.str('TOKEN')
OWNER_GUILD_IDS = env.list('OWNER_GUILD_IDS', default=[], subcast=int)
OWNER_IDS = env.list('OWNER_IDS', default=[], subcast=int)

DISCORD_LOG_LEVEL = env.str('DISCORD_LOG_LEVEL')
BOT_LOG_LEVEL = env.str('BOT_LOG_LEVEL')
DEFAULT_PREFIX = env.str('DEFAULT_PREFIX')

MONGO_IP = env.str('MONGO_IP')
MONGO_DB_NAME = env.str('MONGO_DB_NAME')
MONGO_DB_USERNAME = env.str('MONGO_DB_USERNAME')
MONGO_DB_PASSWORD = env.str('MONGO_DB_PASSWORD')
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

OPENAI_API_KEY = env.str('OPENAI_API_KEY', default=None)
OPENAI_MODEL = env.str('OPENAI_MODEL', default=None)
OPENAI_IMAGE_MODEL = env.str('OPENAI_IMAGE_MODEL', default=None)
OPENAI_MAX_TOKEN = env.str('OPENAI_MAX_TOKEN', default=None)

PANEL_URL = env.str('PANEL_URL', default=None)
PANEL_API_KEY = env.str('PANEL_API_KEY', default=None)

GEMINI_API_KEY = env.str('GEMINI_API_KEY', default=None)
GEMINI_CHAT_MODEL = env.str('GEMINI_CHAT_MODEL', default=None)
GEMINI_IMAGE_MODEL = env.str('GEMINI_IMAGE_MODEL', default=None)

RAPID_API_KEY = env.str('RAPID_API_KEY', default=None)

FLYFF_IP_ADDRESS = env.str('FLYFF_IP_ADDRESS', default=None)

LAVALINK_HOST = env.str('LAVALINK_HOST')
LAVALINK_PORT = env.str('LAVALINK_PORT')
LAVALINK_PASSWORD = env.str('LAVALINK_PASSWORD')

YTMUSIC_CREDENTIALS_TYPE = env.str('YTMUSIC_CREDENTIALS_TYPE')
YTMUSIC_CREDENTIALS_JSON = env.str('YTMUSIC_CREDENTIALS_JSON')
YTMUSIC_BRAND_ACCOUNT_ID = env.str('YTMUSIC_BRAND_ACCOUNT_ID')
YTMUSIC_CLIENT_ID = env.str('YTMUSIC_CLIENT_ID')
YTMUSIC_CLIENT_SECRET = env.str('YTMUSIC_CLIENT_SECRET')
YTMUSIC_COUNTRY = env.str('YTMUSIC_COUNTRY')

SYNC_COMMANDS = env.bool('SYNC_COMMANDS', default=False)
PROXY = env.str('PROXY', default=None)
