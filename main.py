import logging
import os
import shutil

import i18n
from envparse import env

from neonbot.utils.constants import YOUTUBE_TMP_DIR

env.read_envfile()
i18n.load_path.append('./neonbot/lang')
i18n.set('file_format', 'json')
i18n.set('skip_locale_root_data', True)


def main() -> None:
    from neonbot import bot

    shutil.rmtree(YOUTUBE_TMP_DIR, ignore_errors=True)
    os.makedirs(YOUTUBE_TMP_DIR, exist_ok=True)

    bot.run(log_level=logging.getLevelName(env.str('LOG_LEVEL', default='ERROR')))


if __name__ == "__main__":
    main()
