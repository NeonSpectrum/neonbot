import logging
import re
from datetime import timedelta
from typing import Any, Coroutine, cast

from ..helpers.log import Log

log = cast(Log, logging.getLogger(__name__))


def plural(val: int, singular: str, plural: str) -> str:
    return f"{val} {singular if val == 1 else plural}"


def convert_to_seconds(s):
    units = {'s':'seconds', 'm':'minutes', 'h':'hours', 'd':'days', 'w':'weeks'}

    return int(timedelta(**{
        units.get(m.group('unit').lower(), 'seconds'): int(m.group('val'))
        for m in re.finditer(r'(?P<val>\d+)(?P<unit>[smhdw]?)', s, flags=re.I)
    }).total_seconds())
