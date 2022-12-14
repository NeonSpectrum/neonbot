import random
from datetime import datetime

import discord
from discord.utils import find

from neonbot.classes.embed import Embed
from neonbot.models.exchange_gift import ExchangeGiftMember
from neonbot.models.server import Server
from neonbot.utils.exceptions import ExchangeGiftNotRegistered


class ExchangeGift:
    def __init__(self, interaction: discord.Interaction):
        self.server = Server.get_instance(interaction.guild.id)
        self.guild = interaction.guild
        self.user = interaction.user

    def get(self, user_id):
        return find(lambda member: member.user_id == user_id, self.get_all())

    @property
    def member(self):
        return find(lambda member: member.user_id == self.user.id, self.get_all())

    @property
    def budget(self):
        return self.server.exchange_gift.budget

    @property
    def message_id(self):
        return self.server.exchange_gift.message_id

    def get_all(self):
        return self.server.exchange_gift.members

    async def set_message_id(self, message_id: int):
        self.server.exchange_gift.message_id = message_id
        await self.server.save_changes()

    def get_no_wishlist_users(self):
        no_wishlist_users = []

        for member in self.get_all():
            if member.wishlist is None:
                no_wishlist_users.append(member.user_id)

        return no_wishlist_users

    async def set_budget(self, budget):
        self.server.exchange_gift.budget = budget
        await self.server.save_changes()

    async def set_wishlist(self, wishlist: str):
        if not self.member:
            raise ExchangeGiftNotRegistered()

        self.member.wishlist = wishlist

        await self.server.save_changes()

    def get_wishlist(self):
        if not self.member:
            raise ExchangeGiftNotRegistered()

        return self.member.wishlist

    async def register(self):
        self.server.exchange_gift.members.append(ExchangeGiftMember(user_id=self.user.id))
        await self.server.save_changes()

    async def unregister(self):
        if not self.member:
            raise ExchangeGiftNotRegistered()

        self.server.exchange_gift.members.remove(ExchangeGiftMember(user_id=self.user.id))
        await self.server.save_changes()

    async def shuffle(self):
        members = list(map(lambda m: m.user_id, self.get_all()))

        if len(members) <= 1:
            return

        for member in self.get_all():
            chosen_member = random.choice([m for m in members if m != member.user_id])
            members.remove(chosen_member)

            self.member.chosen = chosen_member

            await self.server.save_changes()

    def create_embed_template(self):
        year = datetime.now().strftime('%Y')
        return Embed().set_author('🎁 Exchange Gift ' + year)

    def create_start_template(self):
        from neonbot import bot

        embed = self.create_embed_template()
        embed.set_description(
            'Christmas season is here! It’s also the season for gift giving, so wouldn’t it be wonderful to have a exchange gift event?\n\n'
            'For more info about this event, interact with the buttons below.\n\n'
            '**Note: If you misclick or have a reason to withdraw, '
            'please DM or tag ' + bot.app_info.owner.mention + '.**'
        )

        return embed

    def get_current_info(self):
        members = [self.guild.get_member(member.user_id).mention for member in self.get_all()]

        embed = self.create_embed_template()
        embed.add_field('Budget:', self.budget)
        embed.add_field('Participants:', ' '.join(members), inline=False)

        return embed
