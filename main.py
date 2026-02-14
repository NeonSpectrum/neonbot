import logging
from concurrent.futures import ThreadPoolExecutor

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

    # Clear debug.log on startup
    open('./debug.log', 'w').close()

    logging.getLogger('apscheduler.scheduler').setLevel(logging.ERROR)

    with ThreadPoolExecutor() as executor:
        bot.run(log_level=logging.getLevelName(env.str('LOG_LEVEL', default='ERROR')), executor=executor)


if __name__ == '__main__':
    main()
