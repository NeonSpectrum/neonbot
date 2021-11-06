import nextcord
from addict import Dict as DictToObject

from .embed import Embed
from .view import View


class PlayerControls:
    def __init__(self, player):
        self.player = player
        self.view = None

    def update_buttons(self, views):
        for view in views:
            view.style = nextcord.ButtonStyle.primary

        # ["🔀","⏮️","⏸️","⏭️","🔁"]
        if self.player.connection.is_playing():
            views[2].emoji = "⏸️"
        else:
            views[2].emoji = "▶️"

        if self.player.get_config("repeat") == 'off':
            views[4].emoji = "🔁"
            views[4].style = nextcord.ButtonStyle.secondary
        elif self.player.get_config("repeat") == 'single':
            views[4].emoji = "🔂"
            views[4].style = nextcord.ButtonStyle.primary
        elif self.player.get_config("repeat") == 'all':
            views[4].emoji = "🔁"
            views[4].style = nextcord.ButtonStyle.primary

        if self.player.get_config("shuffle"):
            views[0].style = nextcord.ButtonStyle.primary
        else:
            views[0].style = nextcord.ButtonStyle.secondary

        return views

    async def callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.channel.send(embed=Embed(f"{interaction.user} clicked {button.emoji.name}"), delete_after=3)

        if button.emoji.name == "▶️":  # play
            if self.player.connection.is_paused():
                await self.player.resume()
            else:
                self.player.current_queue = 0
                await self.player.play()
        elif button.emoji.name == "⏸️":  # pause
            await self.player.pause()
        elif button.emoji.name == "⏮️":  # prev
            self.player.current_queue -= 2
            await self.player.next()
        elif button.emoji.name == "⏭️":  # next
            await self.player.next()
        elif button.emoji.name in ("🔁", "🔂"):  # repeat
            modes = ["off", "single", "all"]
            index = (modes.index(self.player.get_config("repeat")) + 1) % 3
            await self.player.repeat(modes[index])
        elif button.emoji.name == "🔀":  # shuffle
            await self.player.shuffle()

    def initialize(self) -> None:
        buttons = [DictToObject(row) for row in [
            {"emoji": "🔀"},
            {"emoji": "⏮️", "disabled": self.player.current_queue == 0},
            {"emoji": "⏸️"},
            {"emoji": "⏭️"},
            {"emoji": "🔁"},
        ]]
        self.update_buttons(buttons)

        self.view = View.create_button(buttons, self.callback, timeout=None)

    def get(self) -> View:
        return self.view

    def refresh(self) -> None:
        if self.view:
            self.view.children = self.update_buttons(self.view.children)
