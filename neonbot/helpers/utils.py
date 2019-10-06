import logging
from typing import cast

from ..helpers.log import Log

log = cast(Log, logging.getLogger(__name__))


def plural(val: int, singular: str, plural: str) -> str:
    return f"{val} {singular if val == 1 else plural}"
