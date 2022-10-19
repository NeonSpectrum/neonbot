import logging

import i18n
from envparse import env

env.read_envfile()
i18n.load_path.append('./neonbot/lang')
i18n.set('file_format', 'json')
i18n.set('skip_locale_root_data', True)


def main() -> None:
    from neonbot import bot

    bot.run(log_level=logging.ERROR)


if __name__ == "__main__":
    main()
