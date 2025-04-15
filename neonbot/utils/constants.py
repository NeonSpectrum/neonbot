TIMEZONE = "Asia/Manila"
LOG_FORMAT = (
    "%(asctime)s [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d]: %(message)s"
)

YOUTUBE_TMP_DIR = "./tmp/youtube_dl"
YOUTUBE_DOWNLOADS_DIR = "./tmp/youtube_dl/downloads"
YOUTUBE_CACHE_DIR = "./tmp/youtube_dl/cache"
PLAYER_CACHE_DIR = "./tmp/players"

PLAYER_CACHE_PATH = "./tmp/players/%s.json"

PERMISSIONS = 8

PAGINATION_EMOJI = ["⏮", "◀", "▶", "⏭", "🗑"]
CHOICES_EMOJI = [
    "\u0031\u20E3",
    "\u0032\u20E3",
    "\u0033\u20E3",
    "\u0034\u20E3",
    "\u0035\u20E3",
    "\u0036\u20E3",
    "\u0037\u20E3",
    "\u0038\u20E3",
    "\u0039\u20E3",
    "\u0040\u20E3",
    "🗑",
]

ICONS = {
    "pokemon": "https://i.imgur.com/3sQh8aN.png",
    "music": "https://i.imgur.com/SBMH84I.png",
    "python": "https://i.imgur.com/vzcWouB.png",
    "github": "https://cdn1.iconfinder.com/data/icons/social-media-vol-1-1/24/_github-512.png",
    "pip": "https://i.imgur.com/vzcWouB.png",
    "google": "https://i.imgur.com/G46fm8J.png",
    "merriam": "https://dictionaryapi.com/images/MWLogo.png",
    "openweather": "https://media.dragstone.com/content/icon-openweathermap-1.png",
    "leaguespy": "https://www.leaguespy.net/images/favicon/favicon-32x32.png",
    "azlyrics": "https://images.azlyrics.com/az_logo_tr.png",
    "semaphone": "https://semaphore.co/images/pages/index/semaphore-icon.png",
    "myanimelist": "https://i.imgur.com/XMQsLF5.png",
    "googletranslate": "https://upload.wikimedia.org/wikipedia/commons/d/db/Google_Translate_Icon.png",
    "openai": "https://i.imgur.com/TAeEnLT.png",
    "green": "https://i.imgur.com/Vk1wdHH.png",
    "red": "https://i.imgur.com/gnfYVjW.png"
}

FFMPEG_BEFORE_OPTIONS = (
    "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -err_detect ignore_err"
)

FFMPEG_OPTIONS = (
    "-vn -ac 2 -ar 48000"
)

YOUTUBE_REGEX = r"^(http(s)?:\/\/)?(((w){3}|music).)?youtu(be|.be)?(\.com)?\/.+"
SPOTIFY_REGEX = r"^(spotify:|https:\/\/[a-z]+\.spotify\.com\/)"

IGNORED_DELETEONCMD = ["eval", "prune"]
EXCLUDED_TYPING = ["eval", "prune", "skip", "chatbot"]

LOGO = """\
 __    _  _______  _______  __    _  _______  _______  _______
|  |  | ||       ||       ||  |  | ||  _    ||       ||       |
|   |_| ||    ___||   _   ||   |_| || |_|   ||   _   ||_     _|
|       ||   |___ |  | |  ||       ||       ||  | |  |  |   |
|  _    ||    ___||  |_|  ||  _    ||  _   | |  |_|  |  |   |
| | |   ||   |___ |       || | |   || |_|   ||       |  |   |
|_|  |__||_______||_______||_|  |__||_______||_______|  |___|
"""
