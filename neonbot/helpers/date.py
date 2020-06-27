from datetime import datetime, timedelta
from typing import Union

from pytz import timezone

from .constants import TIMEZONE


def date() -> datetime:
    return datetime.now(timezone(TIMEZONE))


def date_format(dt: datetime = None) -> str:
    return f"{(dt or date()):%Y-%m-%d %-I:%M:%S %p}"


def format_seconds(secs: Union[int, float]) -> str:
    formatted = str(timedelta(seconds=secs)).split(".")[0]
    if formatted.startswith("0:"):
        return formatted[2:]
    return formatted
