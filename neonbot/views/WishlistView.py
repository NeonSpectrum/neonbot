import discord

from neonbot.classes.exchange_gift import ExchangeGift
from neonbot.views.WishlistModal import WishlistModal


class WishlistView(discord.ui.View):
    def __init__(self, parent: discord.Interaction):
        super().__init__(timeout=None)
        self.parent = parent

    @discord.ui.button(label='Edit your wishlist', custom_id='exchange_gift:edit_wishlist')
    async def edit_wishlist(self, interaction: discord.Interaction, button: discord.ui.Button):
        exchange_gift = ExchangeGift(interaction)

        await interaction.response.send_modal(WishlistModal(self.parent))
