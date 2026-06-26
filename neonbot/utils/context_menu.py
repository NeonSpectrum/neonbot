from typing import TYPE_CHECKING

import discord
from discord import app_commands

from neonbot.discord_ui.embed import Embed
from neonbot.env import CONTEXT_MENU_GUILD_ID, CONTEXT_MENU_GUEST_ROLE_ID, CONTEXT_MENU_MEMBER_ROLE_ID
from neonbot.utils.functions import generate_profile_member_embed

if TYPE_CHECKING:
    from neonbot import NeonBot


def load_context_menu(bot):
    @bot.tree.context_menu(name='Add to Member')
    @app_commands.guilds(discord.Object(id=CONTEXT_MENU_GUILD_ID))
    @app_commands.default_permissions(administrator=True)
    async def add_to_member(interaction: discord.Interaction['NeonBot'], member: discord.Member):
        guest_role = interaction.guild.get_role(CONTEXT_MENU_GUEST_ROLE_ID)
        member_role = interaction.guild.get_role(CONTEXT_MENU_MEMBER_ROLE_ID)

        await member.remove_roles(guest_role)
        await member.add_roles(member_role)

        await interaction.response.send_message(
            embed=Embed(f'{member.mention} added to {member_role.mention} role.'), ephemeral=True
        )

    @bot.tree.context_menu(name='Profile')
    async def profile(interaction: discord.Interaction['NeonBot'], member: discord.Member):
        embed = await generate_profile_member_embed(interaction, member)
        await interaction.response.send_message(embed=embed, ephemeral=True)
