import logging

import termcolor

from .. import env
from .constants import LOG_FORMAT


def colored(*args):
    if env.bool("HEROKU", False):
        return args[0]
    return termcolor.colored(*args)


def cprint(*args):
    if env.bool("HEROKU", False):
        return print(args[0])
    return termcolor.cprint(*args)


class Log(logging.Logger):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.formatter = logging.Formatter(LOG_FORMAT, "%Y-%m-%d %I:%M:%S %p")
        self.setLevel(env.log_level("LOG_LEVEL"))

        self.set_file_handler()
        self.set_console_handler()

    def set_file_handler(self):
        file = logging.FileHandler(filename="debug.log", encoding="utf-8", mode="w")
        file.setFormatter(self.formatter)
        self.addHandler(file)

    def set_console_handler(self):
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(self.formatter)
        self.addHandler(console)

    def cmd(self, ctx, msg, guild=None, channel=None, user=None):
        guild = guild or ctx.guild
        channel = channel or ctx.channel
        user = user or ctx.author

        print()
        self._log(
            logging.INFO,
            f"""
    Guild: {guild}
    Channel: {channel}
    User: {user}
    Message: {str(msg)}""",
            [],
        )


logging.setLoggerClass(Log)
