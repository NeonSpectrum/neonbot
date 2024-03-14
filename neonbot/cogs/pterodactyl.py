import discord
from discord import app_commands
from discord.ext import commands

from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.classes.pterodactyl import Pterodactyl
from neonbot.models.guild import Guild
from neonbot.models.ptero import PteroServer


class PterodactylCog(commands.Cog):
    ptero = app_commands.Group(name='ptero', description='Pterodactyl commands',
                               guild_ids=bot.owner_guilds,
                               default_permissions=discord.Permissions(administrator=True))

    @ptero.command(name='startmonitor')
    async def startmonitor(self, interaction: discord.Interaction, server_id: str) -> None:
        server = Guild.get_instance(interaction.guild.id)

        details = await Pterodactyl(server_id).get_server_details()

        if not details:
            await interaction.response.send_message(embed=Embed("Invalid server id."), ephemeral=True)
            return

        if server_id not in server.ptero.servers:
            server.ptero.servers[server_id] = PteroServer(channel_id=interaction.channel_id)
        else:
            server.ptero.servers[server_id].channel_id = interaction.channel_id

        await server.save_changes()

        bot.scheduler.add_job(
            id='ptero-' + str(interaction.guild.id) + '-' + server_id,
            func=Pterodactyl.start_monitor,
            trigger='interval',
            seconds=15,
            kwargs={
                'channel_id': interaction.channel_id,
                'server_id': server_id
            }
        )

        await interaction.response.send_message(
            embed=Embed(f'Started monitor for `{server_id}` on {interaction.channel.mention}'),
            ephemeral=True
        )

    @ptero.command(name='deletemonitor')
    async def deletemonitor(self, interaction: discord.Interaction, server_id: str) -> None:
        server = Guild.get_instance(interaction.guild.id)

        if server_id not in server.ptero.servers:
            await interaction.response.send_message(embed=Embed("Invalid server id."), ephemeral=True)
            return

        ptero = server.ptero.servers[server_id]
        await bot.delete_message(await bot.get_channel(ptero.channel_id).fetch_message(ptero.message_id))

        del server.ptero.servers[server_id]

        await server.save_changes()

        bot.scheduler.remove_job('ptero-' + str(interaction.guild.id) + '-' + server_id)

        await interaction.response.send_message(
            embed=Embed(f'Removed monitor for `{server_id}` on {interaction.channel.mention}'),
            ephemeral=True
        )


# noinspection PyShadowingNames
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PterodactylCog())
