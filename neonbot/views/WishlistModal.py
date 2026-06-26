from typing import Optional
from typing import TYPE_CHECKING

import discord
from i18n import t

from neonbot.classes.discord_utils.embed import Embed
from neonbot.classes.exchange_gift import ExchangeGift
from neonbot.utils.exceptions import ExchangeGiftNotRegistered

if TYPE_CHECKING:
    from neonbot import NeonBot


class WishlistModal(discord.ui.Modal, title=t('exchange_gift.modal_set_wishlist_title')):
    def __init__(self, parent: Optional[discord.Interaction['NeonBot']] = None):
        super().__init__()
        self.parent = parent

    wishlist = discord.ui.TextInput(
        label=t('exchange_gift.modal_wishlist_label'),
        placeholder=t('exchange_gift.modal_wishlist_placeholder'),
        style=discord.TextStyle.long,
    )

    async def on_submit(self, interaction: discord.Interaction['NeonBot']):
        try:
            wishlist = self.wishlist.value

            exchange_gift = ExchangeGift(interaction)
            await exchange_gift.set_wishlist(wishlist)

            if self.parent:
                await interaction.response.defer()
                await self.parent.edit_original_response(embed=Embed(t('exchange_gift.your_wishlist', wishlist=wishlist)))
            else:
                await interaction.response.send_message(
                    embed=Embed(t('exchange_gift.wishlist_updated')), ephemeral=True
                )
        except ExchangeGiftNotRegistered:
            await interaction.response.send_message(
                embed=Embed(t('exchange_gift.not_registered')), ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(
                embed=Embed(t('exchange_gift.wishlist_save_error')), ephemeral=True
            )
