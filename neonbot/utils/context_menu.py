import discord
from discord import app_commands

from neonbot.classes.embed import Embed


def load_context_menu(bot):
    @bot.tree.context_menu(name='Add to Member')
    @app_commands.guilds(discord.Object(id=1008661677446807713))
    @app_commands.default_permissions(administrator=True)
    async def add_to_member(interaction: discord.Interaction, member: discord.Member):
        guest_role = interaction.guild.get_role(1016294997353570305)
        member_role = interaction.guild.get_role(1008661677446807714)

        await member.remove_roles(guest_role)
        await member.add_roles(member_role)

        await interaction.response.send_message(embed=Embed(f'{member.mention} added to member role.'), ephemeral=True)
