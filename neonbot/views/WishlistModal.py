from typing import Optional
from typing import TYPE_CHECKING

import discord

from neonbot.classes.discord_utils.embed import Embed
from neonbot.classes.exchange_gift import ExchangeGift
from neonbot.utils.exceptions import ExchangeGiftNotRegistered

if TYPE_CHECKING:
    from neonbot import NeonBot


class WishlistModal(discord.ui.Modal, title='Set your wishlist'):
    def __init__(self, parent: Optional[discord.Interaction['NeonBot']] = None):
        super().__init__()
        self.parent = parent

    wishlist = discord.ui.TextInput(
        label='Wishlist',
        placeholder='Type your wishlist here...',
        style=discord.TextStyle.long,
    )

    async def on_submit(self, interaction: discord.Interaction['NeonBot']):
        try:
            wishlist = self.wishlist.value

            exchange_gift = ExchangeGift(interaction)
            await exchange_gift.set_wishlist(wishlist)

            if self.parent:
                await interaction.response.defer()
                await self.parent.edit_original_response(embed=Embed(f'Your wishlist: ```{wishlist}```'))
            else:
                await interaction.response.send_message(
                    embed=Embed('Your wishlist has been updated.'), ephemeral=True
                )
        except ExchangeGiftNotRegistered:
            await interaction.response.send_message(
                embed=Embed('You are not registered for the exchange gift.'), ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(
                embed=Embed('An error occurred while saving your wishlist.'), ephemeral=True
            )
