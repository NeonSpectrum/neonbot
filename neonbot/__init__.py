__title__ = "NeonBot"
__author__ = "NeonSpectrum"
__version__ = "1.1.4"

from .env import env  # isort:skip
from .bot import bot

__all__ = ("bot", "env")
