__title__ = "NeonBot"
__author__ = "NeonSpectrum"
__version__ = "1.1.0"

from .env import env  # isort:skip
from .database import Database  # isort:skip
from .bot import bot  # isort:skip

from . import classes, cogs, helpers
