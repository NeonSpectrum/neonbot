import asyncio
import logging
import os
import shutil
import signal

import i18n
from envparse import env
from dotenv import load_dotenv

load_dotenv()
env.read_envfile()
i18n.load_path.append('./neonbot/lang')
i18n.set('file_format', 'json')
i18n.set('skip_locale_root_data', True)


def main() -> None:
    from neonbot import bot
    from neonbot.utils.constants import YOUTUBE_DOWNLOADS_DIR, PLAYER_CACHE_DIR

    shutil.rmtree(YOUTUBE_DOWNLOADS_DIR, ignore_errors=True)
    os.makedirs(YOUTUBE_DOWNLOADS_DIR, exist_ok=True)
    os.makedirs(PLAYER_CACHE_DIR, exist_ok=True)

    # Clear debug.log on startup
    open('./debug.log', 'w').close()

    loop = asyncio.get_running_loop()

    for signame in (signal.SIGTERM,): 
        loop.add_signal_handler(signame, lambda: asyncio.create_task(bot.close()))

    bot.run(log_level=logging.getLevelName(env.str('LOG_LEVEL', default='ERROR')))


if __name__ == "__main__":
    main()
