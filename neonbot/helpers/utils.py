import logging
from typing import cast

from discord.ext import commands

from ..helpers.log import Log

log = cast(Log, logging.getLogger(__name__))


def plural(val: int, singular: str, plural: str) -> str:
    return f"{val} {singular if val == 1 else plural}"


async def check_args(ctx: commands.Context, arg: str, choices: list) -> bool:
    from ..classes import Embed

    if arg in choices:
        return True
    await ctx.send(embed=Embed(f"Invalid argument. ({' | '.join(choices)})"))
    return False
