import asyncio

import discord

from .. import bot
from ..helpers.constants import PAGINATION_EMOJI
from ..helpers.utils import Embed


class PaginationEmbed:
    def __init__(self, array=[], authorized_users=[]):
        self.bot = bot
        self.array = array
        self.authorized_users = authorized_users

        self.index = 0
        self.embed = Embed()
        self.msg = None

    async def build(self, ctx):
        self.ctx = ctx
        self.title = self.embed.title
        await self._send()

        if len(self.array) > 1:
            asyncio.ensure_future(self._add_reactions())
            await self._listen()

    async def _send(self):
        embed = self.embed.copy()
        embed.description = (
            self.array[self.index].description
            + f"\n\n**Page {self.index+1}/{len(self.array)}**"
        )

        if self.msg:
            return await self.msg.edit(embed=embed)

        self.msg = await self.ctx.send(embed=embed)

    async def _listen(self):
        msg = self.msg

        def check(reaction, user):
            if not user.bot and reaction.emoji != "🗑":
                asyncio.ensure_future(reaction.remove(user))
            return (
                reaction.emoji in PAGINATION_EMOJI
                and user.id in self.authorized_users
                and reaction.message.id == msg.id
            )

        while True:
            try:
                reaction, _ = await self.bot.wait_for(
                    "reaction_add", timeout=60, check=check
                )

                await self._execute_command(PAGINATION_EMOJI.index(reaction.emoji))

                if reaction.emoji == "🗑":
                    await self.msg.delete()

            except asyncio.TimeoutError:
                await msg.clear_reactions()
                break

    async def _add_reactions(self):
        for emoji in PAGINATION_EMOJI:
            try:
                await self.msg.add_reaction(emoji)
            except discord.NotFound:
                break

    async def _execute_command(self, cmd):
        current_index = self.index

        if cmd == 0 and self.index > 0:
            self.index -= 1
        elif cmd == 1 and self.index < len(self.array) - 1:
            self.index += 1

        if current_index != self.index:
            await self._send()

    def set_author(self, **kwargs):
        self.embed.set_author(**kwargs)

    def set_footer(self, **kwargs):
        self.embed.set_footer(**kwargs)
