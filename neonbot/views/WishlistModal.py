import discord

from neonbot.classes.embed import Embed
from neonbot.classes.exchange_gift import ExchangeGift


class WishlistModal(discord.ui.Modal, title='Set your wishlist'):
    def __init__(self, parent: discord.Interaction):
        super().__init__()
        self.parent = parent

    wishlist = discord.ui.TextInput(
        label='Wishlist',
        placeholder='Type your wishlist here...',
        style=discord.TextStyle.long,
    )

    async def on_submit(self, interaction: discord.Interaction):
        wishlist = self.wishlist.value

        exchange_gift = ExchangeGift(interaction)
        await exchange_gift.set_wishlist(wishlist)
        await interaction.response.defer()
        await self.parent.edit_original_response(embed=Embed(f'Your wishlist: ```{wishlist}```'))
