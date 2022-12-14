import discord

from neonbot.classes.embed import Embed
from neonbot.classes.exchange_gift import ExchangeGift
from neonbot.utils.exceptions import ExchangeGiftNotRegistered
from neonbot.views.WishlistModal import WishlistModal
from neonbot.views.WishlistView import WishlistView


class ExchangeGiftView(discord.ui.View):
    def __init__(self, discussion_url: str = None):
        super().__init__(timeout=None)

        if discussion_url:
            self.add_item(
                discord.ui.Button(
                    label='Go to discussions',
                    url=discussion_url,
                    emoji='💬'
                )
            )

    @discord.ui.button(label='Participate', style=discord.ButtonStyle.primary, custom_id='exchange_gift:participate',
                       emoji='✅')
    async def participate(self, interaction: discord.Interaction, button: discord.ui.Button):
        exchange_gift = ExchangeGift(interaction)

        if exchange_gift.member:
            await interaction.response.send_message(
                embed=Embed('You are already registered in the exchange gift event.'),
                ephemeral=True
            )
            return

        await exchange_gift.register()
        await interaction.response.send_message(embed=Embed('You have been registered in the exchange gift event.'),
                                                ephemeral=True)

    @discord.ui.button(label='Wishlist', custom_id='exchange_gift:wishlist', emoji='🎁')
    async def wishlist(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            exchange_gift = ExchangeGift(interaction)
            wishlist = exchange_gift.get_wishlist()

            if not wishlist:
                await interaction.response.send_modal(WishlistModal())
            else:
                view = WishlistView(interaction)
                message = await interaction.response.send_message(embed=Embed(f'Your wishlist: ```{wishlist}```'),
                                                                  view=view,
                                                                  ephemeral=True)

        except ExchangeGiftNotRegistered as error:
            await interaction.response.send_message(embed=Embed(error), ephemeral=True)

    @discord.ui.button(label='Get event info', custom_id='exchange_gift:get_event_info', emoji='📄')
    async def get_event_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        exchange_gift = ExchangeGift(interaction)
        await interaction.response.send_message(embed=exchange_gift.get_current_info(), ephemeral=True)
