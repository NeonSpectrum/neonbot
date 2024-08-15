from typing import TYPE_CHECKING

import discord
from i18n import t

from .embed import Embed
from .view import View, Button
from .. import bot
from ..enums import Repeat, PlayerState

if TYPE_CHECKING:
    from .player import Player


class PlayerControls:
    def __init__(self, player):
        self.player: Player = player
        self.view = None

    def update_buttons(self, views):
        # ["🔀","⏮️","⏸️","⏭️","🔁"]

        if self.player.shuffle:
            views[0].style = discord.ButtonStyle.primary
        else:
            views[0].style = discord.ButtonStyle.secondary

        views[1].disabled = not (0 <= self.player.current_track -1 < len(self.player.track_list))

        if self.player.connection and self.player.connection.is_playing():
            views[2].emoji = "⏸️"
        else:
            views[2].emoji = "▶️"

        if self.player.repeat == Repeat.OFF:
            views[4].emoji = "🔁"
            views[4].style = discord.ButtonStyle.secondary
        elif self.player.repeat == Repeat.SINGLE:
            views[4].emoji = "🔂"
            views[4].style = discord.ButtonStyle.primary
        elif self.player.repeat == Repeat.ALL:
            views[4].emoji = "🔁"
            views[4].style = discord.ButtonStyle.primary

        if self.player.autoplay:
            views[5].style = discord.ButtonStyle.primary
        else:
            views[5].style = discord.ButtonStyle.secondary

        views[6].disabled = self.player.state == PlayerState.STOPPED

        return views

    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not interaction.user.voice or (
            interaction.user.voice and interaction.user.voice.channel != self.player.connection.channel
        ):
            if not bot.is_owner(interaction.user):
                await bot.send_response(interaction, embed=Embed(t('music.cannot_interact')), ephemeral=True)
                return

        if button.emoji.name == "▶️":  # play
            if self.player.connection.is_paused():
                await self.player.resume(requester=interaction.user)
            else:
                self.player.current_track = 0
                await self.player.play()
        elif button.emoji.name == "⏸️":  # pause
            await self.player.pause(requester=interaction.user)
        elif button.emoji.name == "⏮️":  # prev
            self.player.jump_to_track = self.player.current_track - 1
            self.player.state = PlayerState.JUMPED
            self.player.next()

            await interaction.channel.send(
                embed=Embed(t('music.player_controls_pressed', action='back', user=interaction.user.mention))
            )
        elif button.emoji.name == "⏭️":  # next
            if self.player.connection.is_playing():
                if self.player.current_track != len(self.player.track_list) - 1:
                    self.player.jump_to_track = self.player.current_track + 1
                    self.player.state = PlayerState.JUMPED

                self.player.next()
            else:
                await self.player.after()

            await interaction.channel.send(
                embed=Embed(t('music.player_controls_pressed', action='next', user=interaction.user.mention))
            )
        elif button.emoji.name in ("🔁", "🔂"):  # repeat
            modes = [Repeat.OFF, Repeat.SINGLE, Repeat.ALL]
            index = (modes.index(Repeat(self.player.repeat)) + 1) % 3
            await self.player.set_repeat(modes[index], requester=interaction.user)
        elif button.emoji.name == "🔀":  # shuffle
            await self.player.set_shuffle(requester=interaction.user)
        elif button.emoji.name == "♾️":  # autoplay
            await self.player.set_autoplay(requester=interaction.user)
        elif button.emoji.name == "⏹️": # stop
            await self.player.stop()
            await interaction.channel.send(
                embed=Embed(t('music.player_controls_pressed', action='stop', user=interaction.user.mention))
            )
        elif button.emoji.name == "⏏️": # reset
            await self.player.reset()
            self.player.remove_instance()
            await interaction.channel.send(
                embed=Embed(t('music.player_controls_pressed', action='reset', user=interaction.user.mention))
            )

    def initialize(self) -> None:
        buttons = [
            Button(emoji="🔀"),
            Button(emoji="⏮️", style=discord.ButtonStyle.primary),
            Button(emoji="⏸️", style=discord.ButtonStyle.primary),
            Button(emoji="⏭️", style=discord.ButtonStyle.primary),
            Button(emoji="🔁"),
            Button(emoji="♾️", label="Autoplay"),
            Button(emoji="⏹️", label="Stop"),
            Button(emoji="⏏️", label="Reset"),
        ]
        self.update_buttons(buttons)

        self.view = View.create_button(buttons, self.callback, timeout=None)

    def get(self) -> View:
        return self.view

    def refresh(self) -> None:
        if not self.view:
            return

        views = self.view.children
        self.view.clear_items()

        for button in self.update_buttons(views):
            self.view.add_item(button)
