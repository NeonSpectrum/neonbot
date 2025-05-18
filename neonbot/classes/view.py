import inspect
from typing import Optional, cast

import discord


class Button(discord.ui.Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._callback = None

    def set_callback(self, callback):
        self._callback = callback

    async def callback(self, interaction: discord.Interaction):
        if inspect.iscoroutinefunction(self._callback):
            await self._callback(self, interaction)
        else:
            self._callback(self, interaction)

        if not cast(discord.InteractionResponse, interaction.response).is_done():
            await cast(discord.InteractionResponse, interaction.response).defer()


class View(discord.ui.View):
    def __init__(self, interaction: Optional[discord.Interaction], delete_on_timeout: bool, **kwargs):
        self.interaction = interaction
        self.delete_on_timeout = delete_on_timeout
        super().__init__(**kwargs)

    @staticmethod
    def create_button(data, callback, *, interaction: discord.Interaction = None, timeout=180, delete_on_timeout=False):
        view = View(timeout=timeout, interaction=interaction, delete_on_timeout=delete_on_timeout)

        for button in data:
            button.set_callback(callback)
            view.add_item(button)

        return view

    async def on_timeout(self) -> None:
        self.clear_items()
        self.stop()

        if self.interaction:
            try:
                if self.delete_on_timeout:
                    await self.interaction.delete_original_response()
                else:
                    await self.interaction.edit_original_response(view=self)
            except discord.NotFound:
                pass

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        if isinstance(error, discord.NotFound):
            return

        return await super().on_error(interaction, error, item)
