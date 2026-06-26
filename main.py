import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import i18n
from discord import utils
from envparse import env

env.read_envfile()
i18n.load_path.append('./neonbot/lang')
i18n.set('file_format', 'json')
i18n.set('skip_locale_root_data', True)


async def main() -> None:
    from neonbot.bot import NeonBot
    from neonbot.env import TOKEN

    # Clear debug.log on startup
    open('./debug.log', 'w').close()

    logging.getLogger('apscheduler.scheduler').setLevel(logging.ERROR)

    with ThreadPoolExecutor() as executor:
        bot = NeonBot(executor)

        try:
            utils.setup_logging(
                level=logging.getLevelName(env.str('DISCORD_LOG_LEVEL', default='ERROR')),
            )
            await bot.start(TOKEN)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            await bot.close()


if __name__ == '__main__':
    asyncio.run(main())
