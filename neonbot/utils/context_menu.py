from typing import TYPE_CHECKING

import discord
from discord import app_commands

from neonbot.classes.discord.embed import Embed
from neonbot.utils.functions import generate_profile_member_embed

if TYPE_CHECKING:
    from neonbot import NeonBot


def load_context_menu(bot):
    @bot.tree.context_menu(name='Add to Member')
    @app_commands.guilds(discord.Object(id=1008661677446807713))
    @app_commands.default_permissions(administrator=True)
    async def add_to_member(interaction: discord.Interaction['NeonBot'], member: discord.Member):
        guest_role = interaction.guild.get_role(1016294997353570305)
        member_role = interaction.guild.get_role(1008661677446807714)

        await member.remove_roles(guest_role)
        await member.add_roles(member_role)

        await interaction.response.send_message(
            embed=Embed(f'{member.mention} added to {member_role.mention} role.'), ephemeral=True
        )

    @bot.tree.context_menu(name='Profile')
    async def profile(interaction: discord.Interaction['NeonBot'], member: discord.Member):
        embed = await generate_profile_member_embed(interaction, member)
        await interaction.response.send_message(embed=embed, ephemeral=True)
