import logging
from typing import Any, Coroutine, cast

from ..helpers.log import Log

log = cast(Log, logging.getLogger(__name__))


def plural(val: int, singular: str, plural: str) -> str:
    return f"{val} {singular if val == 1 else plural}"


async def log_exception(log: Log, awaitable: Coroutine[Any, Any, Any]) -> Any:
    try:
        return await awaitable
    except Exception as e:
        log.exception(e)
