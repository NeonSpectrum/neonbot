import logging
import os
import shutil

import i18n
from dotenv import load_dotenv
from envparse import env

load_dotenv()
env.read_envfile()
i18n.load_path.append('./neonbot/lang')
i18n.set('file_format', 'json')
i18n.set('skip_locale_root_data', True)


def main() -> None:
    from neonbot import bot
    from neonbot.utils.constants import PLAYER_CACHE_DIR, YOUTUBE_DOWNLOADS_DIR

    shutil.rmtree(YOUTUBE_DOWNLOADS_DIR, ignore_errors=True)
    os.makedirs(YOUTUBE_DOWNLOADS_DIR, exist_ok=True)
    os.makedirs(PLAYER_CACHE_DIR, exist_ok=True)

    # Clear debug.log on startup
    open('./debug.log', 'w').close()

    bot.run(log_level=logging.getLevelName(env.str('LOG_LEVEL', default='ERROR')))


if __name__ == '__main__':
    main()
