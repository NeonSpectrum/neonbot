import importlib
import sys

import discord
import git
from discord import app_commands
from discord.ext import commands
from lavalink import PlayerManager

from neonbot import bot
from neonbot.classes.embed import Embed

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


class UpdaterCog(commands.Cog):
    @commands.hybrid_command('update')
    @commands.is_owner()
    async def update(self, ctx: commands.Context):
        global module_changed

        repo = git.Repo('.')
        old_hash = repo.head.commit.hexsha

        repo.git.reset('--hard')
        pull_output = repo.git.pull('origin', repo.active_branch.name, verbose=True)
        new_hash = repo.head.commit.hexsha

        if old_hash == new_hash:
            await ctx.send("Already up to date.", ephemeral=True)
            return

        await ctx.reply(embed=Embed(title='Git Pull Result', description=f'```md\n{pull_output}\n```'), ephemeral=True)

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

        await ctx.reply(
            embed=Embed('\n'.join([
                'Updated!',
                f'{len(changed_files)} files changed.',
                f'Python modules: {', '.join(changed_files)}',
            ])),
            ephemeral=True
        )

    @commands.hybrid_command('reload')
    @commands.is_owner()
    async def reload(self, ctx, *, modules: str):
        modules = modules.split(' ')
        cogs_reloaded = []
        module_reloaded = []

        for module in modules:
            module = 'neonbot.' + module.strip()

            if module.startswith('neonbot.cogs') and module in bot.extensions:
                bot.reload_extension(module)
                cogs_reloaded.append(module)
            elif module in sys.modules:
                importlib.reload(sys.modules[module])

                if module == 'neonbot.classes.player':
                    from neonbot.classes.player import Player
                    bot.lavalink.player_manager = PlayerManager(self, Player)

                module_reloaded.append(module)

        await ctx.send(
            embed=Embed('\n'.join([
                'Reloaded!',
                f'Python modules: {', '.join(module_reloaded)}',
                f'Cogs modules: {', '.join(cogs_reloaded)}',
            ])),
            ephemeral=True
        )

    @reload.autocomplete('modules')
    async def reload_autocomplete(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=module, value=module) for module in module_changed if current in module]


# noinspection PyShadowingNames
async def setup(bot):
    await bot.add_cog(UpdaterCog())
