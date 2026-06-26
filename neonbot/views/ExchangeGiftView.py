from typing import TYPE_CHECKING

import discord
from i18n import t

from neonbot.classes.discord_utils.embed import Embed
from neonbot.classes.exchange_gift import ExchangeGift
from neonbot.utils.exceptions import ExchangeGiftNotRegistered
from neonbot.views.WishlistModal import WishlistModal
from neonbot.views.WishlistView import WishlistView

if TYPE_CHECKING:
    from neonbot import NeonBot


class ExchangeGiftView(discord.ui.View):
    def __init__(self, discussion_url: str = None):
        super().__init__(timeout=None)

        if discussion_url:
            self.add_item(discord.ui.Button(label=t('exchange_gift.button_go_to_discussions'), url=discussion_url, emoji='💬'))

    @discord.ui.button(
        label=t('exchange_gift.button_participate'), style=discord.ButtonStyle.primary, custom_id='exchange_gift:participate', emoji='✅'
    )
    async def participate(self, interaction: discord.Interaction['NeonBot'], button: discord.ui.Button):
        exchange_gift = ExchangeGift(interaction)

        if exchange_gift.member:
            await interaction.response.send_message(
                embed=Embed(t('exchange_gift.already_registered')), ephemeral=True
            )
            return

        await exchange_gift.register()
        await interaction.response.send_message(
            embed=Embed(t('exchange_gift.registered')), ephemeral=True
        )

    @discord.ui.button(label=t('exchange_gift.button_my_wishlist'), custom_id='exchange_gift:my_wishlist', emoji='🎁')
    async def my_wishlist(self, interaction: discord.Interaction['NeonBot'], button: discord.ui.Button):
        try:
            exchange_gift = ExchangeGift(interaction)
            wishlist = exchange_gift.get_wishlist()

            if not wishlist:
                await interaction.response.send_modal(WishlistModal())
            else:
                view = WishlistView(interaction)
                message = await interaction.response.send_message(
                    embed=Embed(t('exchange_gift.your_wishlist', wishlist=wishlist)), view=view, ephemeral=True
                )

        except ExchangeGiftNotRegistered as error:
            await interaction.response.send_message(
                embed=Embed(error), ephemeral=True
            )

    @discord.ui.button(label=t('exchange_gift.button_all_wishlist'), custom_id='exchange_gift:all_wishlist', emoji='🎁')
    async def all_wishlist(self, interaction: discord.Interaction['NeonBot'], button: discord.ui.Button):
        try:
            exchange_gift = ExchangeGift(interaction)
            wishlist = exchange_gift.get_wishlist()

            template = []

            for member in exchange_gift.get_all():
                user = interaction.guild.get_member(member.user_id)
                if not user:
                    continue
                template.append(f'{user.mention}\n```{member.wishlist}```')

            embed = exchange_gift.create_wishlist_template()
            embed.set_description(''.join(template))

            message = await interaction.response.send_message(
                embed=embed, ephemeral=True
            )

        except ExchangeGiftNotRegistered as error:
            await interaction.response.send_message(
                embed=Embed(error), ephemeral=True
            )

    @discord.ui.button(label=t('exchange_gift.button_get_event_info'), custom_id='exchange_gift:get_event_info', emoji='📄')
    async def get_event_info(self, interaction: discord.Interaction['NeonBot'], button: discord.ui.Button):
        exchange_gift = ExchangeGift(interaction)
        await interaction.response.send_message(
            embed=exchange_gift.get_current_info(), ephemeral=True
        )
