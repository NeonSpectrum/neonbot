from __future__ import annotations

from typing import Any, Optional

import discord
from discord.ext import commands

from .view import View
from ..helpers.constants import CHOICES_EMOJI, PAGINATION_EMOJI


class Embed(discord.Embed):
    def __init__(self, description: Any = None, **kwargs: Any) -> None:
        if description is not None:
            super().__init__(description=description and str(description), **kwargs)
        else:
            super().__init__(**kwargs)
        self.color = 0x59ABE3

    def add_field(self, name: Any, value: Any, *, inline: bool = True) -> Embed:
        super().add_field(name=name, value=value, inline=inline)
        return self

    def set_author(
        self,
        name: str,
        url: str = discord.Embed.Empty,
        *,
        icon_url: str = discord.Embed.Empty,
    ) -> Embed:
        super().set_author(name=name, url=url, icon_url=icon_url)
        return self

    def set_footer(
        self, text: str = discord.Embed.Empty, *, icon_url: str = discord.Embed.Empty
    ) -> Embed:
        super().set_footer(text=text, icon_url=icon_url)
        return self

    def set_image(self, url: str) -> Embed:
        if url:
            super().set_image(url=url)
        return self

    def set_thumbnail(self, url: Optional[str]) -> Embed:
        if url:
            super().set_thumbnail(url=url)
        return self


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

        self.msg: Optional[discord.Message] = None

    async def build(self) -> None:
        self.authorized_users.append(self.ctx.author.id)
        self.title = self.embed.title
        await self.send()

    async def send(self) -> None:
        embed = self.embed.copy()
        embed.description = self.embeds[self.index].description

        if len(self.embeds) > 1:
            embed.description += f"\n\n**Page {self.index + 1}/{len(self.embeds)}**"

        if self.msg:
            await self.msg.edit(embed=embed)
            return

        buttons = self.get_buttons()

        self.msg = await self.ctx.send(embed=embed, view=buttons)
        buttons.set_message(self.msg)

    def get_buttons(self) -> discord.ui.View:
        async def callback(button: discord.ui.Button, interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                return

            index = PAGINATION_EMOJI.index(button.emoji.name)

            if index == 4: # trash
                await self.bot.delete_message(self.msg)
                return

            self.execute_command(index)
            await self.send()

        return View.create_button([{"emoji": emoji} for emoji in PAGINATION_EMOJI], callback)

    def execute_command(self, cmd: int) -> None:
        if cmd == 0:
            self.index = 0
        elif cmd == 1 and self.index > 0:
            self.index -= 1
        elif cmd == 2 and self.index < len(self.embeds) - 1:
            self.index += 1
        elif cmd == 3:
            self.index = len(self.embeds) - 1


class EmbedChoices:
    def __init__(self, ctx: commands.Context, entries: list) -> None:
        self.ctx = ctx
        self.bot = ctx.bot
        self.entries = entries

    async def build(self) -> EmbedChoices:
        if not self.entries:
            self.value = -1
            await self.ctx.send(embed=Embed("Empty choices."), delete_after=5)
            return self

        await self.send_choices()

        return self

    async def send_choices(self) -> None:
        embed = Embed(title=f"Choose 1-{len(self.entries)} below.")

        for index, entry in enumerate(self.entries, start=1):
            embed.add_field(f"{index}. {entry['title']}", entry['url'], inline=False)

        buttons = self.get_buttons()

        self.msg = await self.ctx.send(embed=embed, view=buttons)

        await buttons.wait()

    def get_buttons(self) -> discord.ui.View:
        async def callback(button: discord.ui.Button, interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                return

            if button.emoji and button.emoji.name == CHOICES_EMOJI[-1]:
                self.value = -1
            else:
                self.value = int(button.label) - 1

            button.view.stop()
            await self.bot.delete_message(self.msg)


        buttons = [
            {"label": 1},
            {"label": 2},
            {"label": 3},
            {"label": 4},
            {"label": 5},
            {"emoji": CHOICES_EMOJI[-1]},
        ]

        return View.create_button(buttons, callback)
