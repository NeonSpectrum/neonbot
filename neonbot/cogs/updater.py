import importlib
import sys
from typing import TYPE_CHECKING

import discord
import git
from discord import app_commands
from discord.ext import commands
from discord.ui import View

from neonbot.discord_ui.decorators import is_owner
from neonbot.discord_ui.embed import Embed
from neonbot.discord_ui.select_choices import SelectChoices
from neonbot.music.lavalink_client import PlayerManager
from neonbot.utils.constants import ICONS

if TYPE_CHECKING:
    from neonbot import NeonBot

ROOT_FOLDERS = (
    'assets',
    'cogs',
    'core',
    'ai',
    'music',
    'features',
    'discord_ui',
    'lang',
    'models',
    'utils',
)

module_changed = []


class UpdaterCog(commands.Cog):
    @app_commands.command(name='update')
    @is_owner(app=True)
    async def update(self, interaction: discord.Interaction['NeonBot']):
        global module_changed

        repo = git.Repo('.')
        old_hash = repo.head.commit.hexsha

        repo.git.reset('--hard')
        pull_output = repo.git.pull('origin', repo.active_branch.name, verbose=True)
        new_hash = repo.head.commit.hexsha

        if old_hash == new_hash:
            await interaction.response.send_message(embed=Embed('Already up to date.'), ephemeral=True)
            return

        changed_files = []

        if repo.head.commit.parents:
            parent = repo.head.commit.parents[0]
            changed_files = [
                item.a_path
                for item in repo.head.commit.diff(parent)
                if item.a_path and item.a_path.endswith('.py')
            ]

        module_changed = []

        for file_path in changed_files:
            module_name = file_path.replace('/', '.').removesuffix('.py')
            if module_name in sys.modules:
                module_changed.append(module_name)

        embed = Embed('\n'.join([
            f'{len(changed_files)} files changed.',
            f'Python modules: {", ".join(module_changed)}',
            f'```\n{pull_output}\n```'
        ]))
        embed.set_author('Updated!', icon_url=ICONS['github'])

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='reload')
    @is_owner(app=True)
    async def reload(self, interaction: discord.Interaction['NeonBot'], module_list: str = None):
        if module_list:
            modules = module_list.split(',')
            embed = await self.reload_modules(interaction, modules)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif len(module_changed) > 0:
            select = SelectChoices(
                'Select modules to reload...',
                module_changed,
            )

            async def callback(_):
                _embed = await self.reload_modules(interaction, select.values)
                await interaction.edit_original_response(embed=_embed, view=None)

            select.callback = callback

            view = View()
            view.add_item(select)

            await interaction.response.send_message(view=view, ephemeral=True)
        else:
            await interaction.response.send_message(embed=Embed('Empty module list.'), ephemeral=True)

    async def reload_modules(self, interaction, modules):
        cogs_reloaded = []
        module_reloaded = []

        for module in modules:
            if module.startswith('neonbot.cogs') and module in interaction.client.extensions:
                await interaction.client.reload_extension(module)
                cogs_reloaded.append(module)
            elif module in sys.modules:
                importlib.reload(sys.modules[module])

                if module == 'neonbot.music.player':

                    new_players = {}

                    for guild_id, player in interaction.client.lavalink.player_manager.players.items():
                        new_players[guild_id] = {
                            'ctx': player.ctx,
                            'vc': player.voice_channel,
                            'current': player.current,
                            'current_queue': player.current_queue,
                            'last_track': player.last_track,
                            'track_list': player.track_list.copy(),
                            'shuffled_list': player.shuffled_list.copy(),
                            'autoplay_list': player.autoplay_list.copy(),
                            'messages': player.messages,
                            'is_auto_paused': player.is_auto_paused,
                            'channel_id': player.channel_id,
                        }

                    interaction.client.lavalink.player_manager = PlayerManager(interaction.client.lavalink)

                    for guild_id, new_player in new_players.items():
                        player = interaction.client.lavalink.player_manager.create(guild_id)
                        player.__dict__.update(new_player)

                module_reloaded.append(module)

        embed = Embed()
        embed.set_author('Reloaded!', icon_url=ICONS['github'])

        if len(module_reloaded) > 0:
            embed.add_field('Python modules', f'```\n{"\n".join(module_reloaded)}\n```', inline=False)

        if len(cogs_reloaded) > 0:
            embed.add_field('Cogs modules', f'```\n{"\n".join(cogs_reloaded)}\n```', inline=False)

        return embed


async def setup(bot):
    await bot.add_cog(UpdaterCog())
