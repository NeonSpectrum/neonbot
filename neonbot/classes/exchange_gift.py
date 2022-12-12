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

    def get_all(self):
        return self.server.exchange_gift.members

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
        return Embed().set_author('🎁 Exchange Gift for ' + year)
