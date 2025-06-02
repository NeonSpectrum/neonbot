from typing import cast

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
            self.add_item(discord.ui.Button(label='Go to discussions', url=discussion_url, emoji='💬'))

    @discord.ui.button(
        label='Participate', style=discord.ButtonStyle.primary, custom_id='exchange_gift:participate', emoji='✅'
    )
    async def participate(self, interaction: discord.Interaction, button: discord.ui.Button):
        exchange_gift = ExchangeGift(interaction)

        if exchange_gift.member:
            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed('You are already registered in the exchange gift event.'), ephemeral=True
            )
            return

        await exchange_gift.register()
        await cast(discord.InteractionResponse, interaction.response).send_message(
            embed=Embed('You have been registered in the exchange gift event.'), ephemeral=True
        )

    @discord.ui.button(label='My Wishlist', custom_id='exchange_gift:my_wishlist', emoji='🎁')
    async def my_wishlist(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            exchange_gift = ExchangeGift(interaction)
            wishlist = exchange_gift.get_wishlist()

            if not wishlist:
                await cast(discord.InteractionResponse, interaction.response).send_modal(WishlistModal())
            else:
                view = WishlistView(interaction)
                message = await cast(discord.InteractionResponse, interaction.response).send_message(
                    embed=Embed(f'Your wishlist: ```{wishlist}```'), view=view, ephemeral=True
                )

        except ExchangeGiftNotRegistered as error:
            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed(error), ephemeral=True
            )

    @discord.ui.button(label='All Wishlist', custom_id='exchange_gift:all_wishlist', emoji='🎁')
    async def all_wishlist(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            exchange_gift = ExchangeGift(interaction)
            wishlist = exchange_gift.get_wishlist()

            template = []

            for member in exchange_gift.get_all():
                user = interaction.guild.get_member(member.user_id)
                template.append(f'{user.mention}\n```{member.wishlist}```')

            embed = exchange_gift.create_wishlist_template()
            embed.set_description(''.join(template))

            message = await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=embed, ephemeral=True
            )

        except ExchangeGiftNotRegistered as error:
            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed(error), ephemeral=True
            )

    @discord.ui.button(label='Get event info', custom_id='exchange_gift:get_event_info', emoji='📄')
    async def get_event_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        exchange_gift = ExchangeGift(interaction)
        await cast(discord.InteractionResponse, interaction.response).send_message(
            embed=exchange_gift.get_current_info(), ephemeral=True
        )
