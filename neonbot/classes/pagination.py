import asyncio
from typing import Optional

import discord
from discord.ext import commands

from ..helpers.constants import PAGINATION_EMOJI
from ..helpers.utils import Embed


class PaginationEmbed:
    """
    Initializes a pagination embed that has a function
    previous, next and delete.

    You cannot control this after the timeout expires. Defaults to 60s
    """

    def __init__(
        self,
        ctx: commands.Context,
        embeds: list = [],
        authorized_users: Optional[list] = None,
        timeout: Optional[int] = None,
    ) -> None:
        self.bot = ctx.bot
        self.ctx = ctx
        self.embeds = embeds
        self.authorized_users = authorized_users or []
        self.timeout = timeout or 60

        self.index = 0
        self.embed = Embed()

        self.msg: discord.Message = None

    async def build(self) -> None:
        self.authorized_users.append(self.ctx.author.id)
        self.title = self.embed.title
        await self._send()

        if len(self.embeds) > 1:
            asyncio.gather(self._add_reactions(), self._listen())

    async def _send(self) -> None:
        embed = self.embed.copy()
        embed.description = self.embeds[self.index].description

        if len(self.embeds) > 1:
            embed.description += f"\n\n**Page {self.index+1}/{len(self.embeds)}**"

        if self.msg:
            return await self.msg.edit(embed=embed)

        self.msg = await self.ctx.send(embed=embed)

    async def _listen(self) -> None:
        """Listens to react of the user and execute commands."""

        msg = self.msg

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            if not user.bot and reaction.emoji != "🗑":
                asyncio.ensure_future(reaction.remove(user))
            return (
                reaction.emoji in PAGINATION_EMOJI
                and user.id in self.authorized_users
                and reaction.message.id == msg.id
            )

        try:
            reaction, _ = await self.bot.wait_for(
                "reaction_add", timeout=self.timeout, check=check
            )

            await self._execute_command(PAGINATION_EMOJI.index(reaction.emoji))

            if reaction.emoji == "🗑":
                return await self.msg.delete()
        except asyncio.TimeoutError:
            await msg.clear_reactions()
        else:
            await self._listen()

    async def _add_reactions(self) -> None:
        for emoji in PAGINATION_EMOJI:
            try:
                await self.msg.add_reaction(emoji)
            except discord.NotFound:
                break

    async def _request_jump(self) -> None:
        request_msg = await self.ctx.send(
            embed=Embed(f"Enter page number (1-{len(self.embeds)}):")
        )

        def check(m: discord.Message) -> bool:
            if m.author.bot:
                return False

            if m.content.isdigit():
                self.bot.loop.create_task(m.delete())
                if (
                    int(m.content) >= 0
                    and int(m.content) <= len(self.embeds)
                    and m.channel.id == self.ctx.channel.id
                ):
                    return True

            return False

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=10)
        except asyncio.TimeoutError:
            pass
        else:
            self.index = int(msg.content) - 1
        finally:
            await request_msg.delete()

    async def _execute_command(self, cmd: int) -> None:
        current_index = self.index

        if cmd == 0:
            self.index = 0
        elif cmd == 1 and self.index > 0:
            self.index -= 1
        elif cmd == 2 and self.index < len(self.embeds) - 1:
            self.index += 1
        elif cmd == 3:
            self.index = len(self.embeds) - 1
        elif cmd == 4:
            await self._request_jump()

        if current_index != self.index:
            await self._send()
