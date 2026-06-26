from typing import TYPE_CHECKING

import discord
from i18n import t

from neonbot.views.WishlistModal import WishlistModal

if TYPE_CHECKING:
    from neonbot import NeonBot


class WishlistView(discord.ui.View):
    def __init__(self, parent: discord.Interaction['NeonBot']):
        super().__init__(timeout=None)
        self.parent = parent

    @discord.ui.button(label=t('exchange_gift.button_edit_wishlist'), custom_id='exchange_gift:edit_wishlist')
    async def edit_wishlist(self, interaction: discord.Interaction['NeonBot'], button: discord.ui.Button):
        await interaction.response.send_modal(WishlistModal(self.parent))
