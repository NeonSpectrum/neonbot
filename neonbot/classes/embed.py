from __future__ import annotations

from typing import Any, Optional

import discord

from .view import View, Button
from ..utils.constants import CHOICES_EMOJI, PAGINATION_EMOJI


class Embed(discord.Embed):
    def __init__(self, description: Any = None, **kwargs: Any) -> None:
        if description is not None:
            super().__init__(description=description and str(description).strip(), **kwargs)
        else:
            super().__init__(**kwargs)
        self.color = 0xE91E63

    def add_field(self, name: Any, value: Any, *, inline: bool = True) -> Embed:
        super().add_field(name=name, value=value, inline=inline)
        return self

    def set_author(
        self,
        name: str,
        url: str = None,
        *,
        icon_url: str = None,
    ) -> Embed:
        super().set_author(name=name, url=url, icon_url=icon_url)
        return self

    def set_footer(
        self, text: str = None, *, icon_url: str = None
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
        interaction: discord.Interaction,
        embeds=None,
        authorized_users: Optional[list] = None,
        timeout: Optional[int] = 60,
    ) -> None:
        if embeds is None:
            embeds = []
        self.interaction = interaction
        self.embeds = embeds
        self.authorized_users = authorized_users or []
        self.timeout = timeout
        self.title = None

        self.index = 0
        self.embed = Embed()

    async def build(self) -> None:
        self.authorized_users.append(self.interaction.user.id)
        self.title = self.embed.title
        await self.send()

    async def send(self) -> None:
        embed = self.embed.copy()
        embed.description = self.embeds[self.index].description
        buttons = None

        if len(self.embeds) > 1:
            embed.description += f"\n\n**Page {self.index + 1}/{len(self.embeds)}**"
            buttons = self.get_buttons()

        if not self.interaction.response.is_done():
            await self.interaction.response.send_message(embed=embed, view=buttons)
        else:
            await self.interaction.edit_original_response(embed=embed, view=buttons)

    def get_buttons(self) -> View:
        async def callback(button: discord.ui.Button, interaction: discord.Interaction):
            if interaction.user != self.interaction.user:
                return

            index = PAGINATION_EMOJI.index(button.emoji.name)

            if index == 4:  # trash
                await self.interaction.delete_original_response()
                return

            self.execute_command(index)
            await self.send()

        buttons = [
            Button(emoji=emoji)
            for emoji in PAGINATION_EMOJI
        ]

        return View.create_button(buttons, callback, interaction=self.interaction, timeout=self.timeout)

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
    def __init__(self, interaction: discord.Interaction, entries: list, timeout: Optional[int] = 30) -> None:
        self.interaction = interaction
        self.entries = entries
        self.value = None
        self.timeout = timeout

    async def build(self) -> EmbedChoices:
        self.value = -1

        if not self.entries:
            await self.send_message(embed=Embed("Empty choices."), ephemeral=True)
        else:
            await self.send_choices()

        return self

    async def send_message(self, *args, **kwargs):
        if self.interaction.response.is_done():
            await self.interaction.followup.send(*args, **kwargs)
        else:
            await self.interaction.response.send_message(*args, **kwargs)

    async def send_choices(self) -> None:
        embed = Embed(title=f"Choose 1-{len(self.entries)} below.")

        for index, entry in enumerate(self.entries, start=1):
            embed.add_field(f"{index}. {entry['title']}", entry['url'], inline=False)

        buttons = self.get_buttons()

        await self.send_message(embed=embed, view=buttons)

        await buttons.wait()

    def get_buttons(self) -> discord.ui.View:
        async def callback(button: discord.ui.Button, interaction: discord.Interaction):
            if interaction.user != self.interaction.user:
                return

            if button.emoji and button.emoji.name == CHOICES_EMOJI[-1]:
                self.value = -1
            else:
                self.value = int(button.label) - 1

            button.view.stop()

        buttons = [
            Button(label=1),
            Button(label=2),
            Button(label=3),
            Button(label=4),
            Button(label=5),
            Button(emoji=CHOICES_EMOJI[-1]),
        ]

        return View.create_button(buttons, callback, interaction=self.interaction, timeout=self.timeout,
                                  delete_on_timeout=True)
