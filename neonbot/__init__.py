__title__ = "NeonBot"
__author__ = "NeonSpectrum"
__version__ = "1.1.3"


from .env import env  # isort:skip
from .helpers import log  # isort:skip
from .database import Database  # isort:skip
from .bot import bot  # isort:skip

from . import classes, cogs, helpers

music = bot.music
game = bot.game

__all__ = (
    "env",
    "Database",
    "log",
    "bot",
    "classes",
    "cogs",
    "helpers",
    "music",
    "game",
)
