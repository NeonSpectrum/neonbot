NAME = 'NeonBot'
AUTHOR = 'NeonSpectrum'
VERSION = '1.0.0'

TIMEZONE = "Asia/Manila"
LOG_FORMAT = '%(asctime)s:%(levelname)s:%(name)s: %(message)s'

PAGINATION_EMOJI = ["◀", "▶", "🗑"]
CHOICES_EMOJI = ['\u0031\u20E3', '\u0032\u20E3', '\u0033\u20E3', '\u0034\u20E3', '\u0035\u20E3', '🗑']

FFMPEG_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -err_detect ignore_err"

YOUTUBE_REGEX = r"^(http(s)?:\/\/)?((w){3}.)?youtu(be|.be)?(\.com)?\/.+"

LOGO = """\
 __    _  _______  _______  __    _  _______  _______  _______   
|  |  | ||       ||       ||  |  | ||  _    ||       ||       |
|   |_| ||    ___||   _   ||   |_| || |_|   ||   _   ||_     _|
|       ||   |___ |  | |  ||       ||       ||  | |  |  |   |
|  _    ||    ___||  |_|  ||  _    ||  _   | |  |_|  |  |   |
| | |   ||   |___ |       || | |   || |_|   ||       |  |   |
|_|  |__||_______||_______||_|  |__||_______||_______|  |___|
"""