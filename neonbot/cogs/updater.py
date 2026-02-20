import asyncio
import sys

import discord
import git
from discord import app_commands
from discord.ext import commands
from lavalink import PlayerManager

from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.utils.constants import ICONS

ROOT_FOLDERS = (
    'assets',
    'classes',
    'cogs',
    'enums',
    'lang',
    'models',
    'utils',
    'views'
)

module_changed = []


async def is_owner(interaction: discord.Interaction) -> bool:
    if interaction.user.id not in bot.owner_ids:
        await interaction.response.send_message(
            embed=Embed("You do not have permission to use this command."), ephemeral=True
        )
        return False

    return True


class UpdaterCog(commands.Cog):
    @app_commands.command(name='update')
    @app_commands.check(is_owner)
    async def update(self, interaction: discord.Interaction):
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
            module_name = file_path.replace('/', '.').rstrip('.py')
            if module_name in sys.modules:
                module_changed.append(module_name)

        embed = Embed('\n'.join([
            f'{len(changed_files)} files changed.',
            f'Python modules: {', '.join(module_changed)}',
            f'```md\n{pull_output}\n```'
        ]))
        embed.set_author('Updated!', icon_url=ICONS['github'])

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='reload')
    @app_commands.check(is_owner)
    async def reload(self, interaction: discord.Interaction):
        from neonbot.classes.player import Player

        new_players = {}

        for guild_id, player in bot.lavalink.player_manager.players.items():
            new_players[guild_id] = {
                'ctx': player.ctx,
                'vc': player.vc,
                'current': player.current,
                'current_queue': player.current_queue,
                'last_track': player.last_track,
                'track_list': player.track_list.copy(),
                'shuffled_list': player.shuffled_list.copy(),
                'autoplay_list': player.autoplay_list.copy(),
                'messages': player.messages,
                'is_auto_paused': player.is_auto_paused,
                'channel_id': player.channel_id,
                'position': player.position
            }

        bot.lavalink.player_manager.players = {}
        bot.lavalink.player_manager = PlayerManager(bot.lavalink, Player)

        # noinspection PyShadowingNames
        async def replace(guild_id, new_player):
            player = bot.lavalink.player_manager.create(guild_id)
            position = new_player.pop('position')
            player.__dict__.update(new_player)

        await asyncio.gather(
            *[replace(guild_id, new_player) for guild_id, new_player in new_players.items()]
        )

        await interaction.response.send_message('reloaded')

        # select = SelectChoices(
        #     'Select modules to reload...',
        #     module_changed,
        # )
        #
        # async def callback(_):
        #     modules = select.values
        #     cogs_reloaded = []
        #     module_reloaded = []
        #
        #     for module in modules:
        #         if module.startswith('neonbot.cogs') and module in bot.extensions:
        #             bot.reload_extension(module)
        #             cogs_reloaded.append(module)
        #         elif module in sys.modules:
        #             importlib.reload(sys.modules[module])
        #
        #             if module == 'neonbot.classes.player':
        #                 from neonbot.classes.player import Player
        #
        #                 new_players = {}
        #
        #                 for guild_id, player in bot.lavalink.player_manager.players.items():
        #                     new_players[guild_id] = {
        #                         'ctx': player.ctx,
        #                         'vc': player.vc,
        #                         'current': player.current,
        #                         'current_queue': player.current_queue,
        #                         'last_track': player.last_track,
        #                         'track_list': player.track_list.copy(),
        #                         'shuffled_list': player.shuffled_list.copy(),
        #                         'autoplay_list': player.autoplay_list.copy(),
        #                         'messages': player.messages,
        #                         'is_auto_paused': player.is_auto_paused,
        #                         'channel_id': player.channel_id,
        #                         'position': player.position
        #                     }
        #
        #                 bot.lavalink.player_manager = PlayerManager(bot.lavalink, Player)
        #
        #                 # noinspection PyShadowingNames
        #                 async def replace(guild_id, new_player):
        #                     player = bot.lavalink.player_manager.create(guild_id)
        #                     position = new_player.pop('position')
        #                     player.__dict__.update(new_player)
        #                     await player.execute_fn_without_message(
        #                         player.play(player.current, start_time=position)
        #                     )
        #
        #                 await asyncio.gather(
        #                     *[replace(guild_id, new_player) for guild_id, new_player in new_players.items()]
        #                 )
        #
        #             module_reloaded.append(module)
        #
        #     embed = Embed()
        #     embed.set_author('Reloaded!', icon_url=bot.user.display_avatar)
        #
        #     if len(module_reloaded) > 0:
        #         embed.add_field('Python modules', f'```\n{'\n'.join(module_reloaded)}\n```', inline=False)
        #
        #     if len(cogs_reloaded) > 0:
        #         embed.add_field('Cogs modules', f'```\n{'\n'.join(cogs_reloaded)}\n```', inline=False)
        #
        #     await interaction.edit_original_response(embed=embed, view=None)
        #
        # select.callback = callback
        #
        # view = View()
        # view.add_item(select)
        #
        # await interaction.response.send_message(view=view, ephemeral=True)


# noinspection PyShadowingNames
async def setup(bot):
    await bot.add_cog(UpdaterCog())
