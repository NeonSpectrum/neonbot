from typing import Union

from discord.ext import commands

from .embed import Embed


class Required(commands.Converter):
    def __init__(self, *args: str) -> None:
        self.req_args = args

    async def convert(self, ctx: commands.Context, argument: str) -> Union[bool, str]:
        if argument in self.req_args:
            return argument

        await ctx.send(embed=Embed(f"Invalid argument. ({' | '.join(self.req_args)})"))
        return False
