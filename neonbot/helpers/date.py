from datetime import datetime, timedelta

from pytz import timezone

from .constants import TIMEZONE


def date():
    return datetime.now(timezone(TIMEZONE))


def date_format(dt=None):
    return f"{(dt or date()):%Y-%m-%d %-I:%M:%S %p}"


def format_seconds(secs, format=0):
    formatted = str(timedelta(seconds=secs))
    if formatted.startswith("0:"):
        return formatted[2:]
    return formatted
