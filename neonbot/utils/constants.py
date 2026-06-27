TIMEZONE = 'Asia/Manila'
LOG_FORMAT = '%(asctime)s [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d]: %(message)s'

PLAYER_CACHE_DIR = './tmp/players'

PLAYER_CACHE_PATH = './tmp/players/%s.json'

PERMISSIONS = 8

PAGINATION_EMOJI = ['⏮', '◀', '▶', '⏭', '🗑']
CHOICES_EMOJI = [
    '\u0031\u20e3',
    '\u0032\u20e3',
    '\u0033\u20e3',
    '\u0034\u20e3',
    '\u0035\u20e3',
    '\u0036\u20e3',
    '\u0037\u20e3',
    '\u0038\u20e3',
    '\u0039\u20e3',
    '\u0040\u20e3',
    '🗑',
]

ICONS = {
    'pokemon': 'https://i.imgur.com/3sQh8aN.png',
    'music': 'https://i.imgur.com/SBMH84I.png',
    'python': 'https://i.imgur.com/vzcWouB.png',
    'github': 'https://github.githubassets.com/favicons/favicon.png',
    'pip': 'https://i.imgur.com/vzcWouB.png',
    'google': 'https://i.imgur.com/G46fm8J.png',
    'openweather': 'https://media.dragstone.com/content/icon-openweathermap-1.png',
    'leaguespy': 'https://www.leaguespy.net/images/favicon/favicon-32x32.png',
    'semaphone': 'https://semaphore.co/images/pages/index/semaphore-icon.png',
    'green': 'https://i.imgur.com/Vk1wdHH.png',
    'red': 'https://i.imgur.com/gnfYVjW.png',
    'deezer': 'https://i.imgur.com/zIMXnXD.png',
    'youtube': 'https://i.imgur.com/wCADAJY.png',
    'applemusic': 'https://i.imgur.com/1nu2yo5.png',
    'spotify': 'https://i.imgur.com/Yby9AcE.png'
}

FFMPEG_BEFORE_OPTIONS = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'

FFMPEG_OPTIONS = '-vn -loglevel quiet'

YOUTUBE_REGEX = r'^(http(s)?:\/\/)?(((w){3}|music).)?youtu(be|.be)?(\.com)?\/.+'
YOUTUBE_PLAYLIST_REGEX = r'(?:https?://)?(?:www\.)?(?:youtube\.com/playlist\?list=|youtu\.be/playlist\?list=|youtube\.com/watch\?v=[^&]+&list=)([a-zA-Z0-9_-]+)'
SPOTIFY_REGEX = r'^(spotify:|https:\/\/[a-z]+\.spotify\.com\/)'

IGNORED_DELETEONCMD = ['eval', 'prune']
EXCLUDED_TYPING = ['eval', 'prune', 'skip', 'chatbot']

LOGO = """\
 __    _  _______  _______  __    _  _______  _______  _______
|  |  | ||       ||       ||  |  | ||  _    ||       ||       |
|   |_| ||    ___||   _   ||   |_| || |_|   ||   _   ||_     _|
|       ||   |___ |  | |  ||       ||       ||  | |  |  |   |
|  _    ||    ___||  |_|  ||  _    ||  _   | |  |_|  |  |   |
| | |   ||   |___ |       || | |   || |_|   ||       |  |   |
|_|  |__||_______||_______||_|  |__||_______||_______|  |___|
"""
