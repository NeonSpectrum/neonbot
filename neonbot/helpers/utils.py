import asyncio
import logging
import re
from datetime import timedelta
from typing import cast

from ..helpers.log import Log

log = cast(Log, logging.getLogger(__name__))


def plural(val: int, singular_noun: str, plural_noun: str) -> str:
    return f"{val} {singular_noun if val == 1 else plural_noun}"


def convert_to_seconds(s) -> int:
    units = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days', 'w': 'weeks'}

    return int(timedelta(**{
        units.get(m.group('unit').lower(), 'seconds'): int(m.group('val'))
        for m in re.finditer(r'(?P<val>\d+)(?P<unit>[smhdw]?)', s, flags=re.I)
    }).total_seconds())


async def shell_exec(command: str) -> str:
    process = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    return stdout.decode().strip()

def get_index(arr: list, index: int) -> any:
    try:
        return arr[index]
    except IndexError:
        return None