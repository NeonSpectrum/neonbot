import importlib
import sys

import git
from discord.ext import commands

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


class UpdateCog(commands.Cog):
    @commands.hybrid_command('update')
    @commands.is_owner()
    async def update(self, ctx: commands.Context):
        global module_changed

        repo = git.Repo('.')
        old_hash = repo.head.commit.hexsha

        repo.git.reset('--hard')
        pull_info = repo.git.pull()
        new_hash = repo.head.commit.hexsha

        if old_hash == new_hash:
            await ctx.send("Already up to date.", ephemeral=True)
            return

        changed_files = []

        if pull_info and pull_info[0][2]:
            commit = repo.head.commit
            changed_files = [diff.a_path for diff in commit.diff(commit.parents[0]) if
                             diff.a_path.endswith('.py')]

        for file_path in changed_files:
            module_name = file_path.replace('/', '.').rstrip('.py')
            if module_name in sys.modules:
                module_changed.append(module_name)

        await ctx.send(
            embed=Embed('\n'.join([
                'Updated!',
                f'{len(changed_files)} files changed.',
                f'Python modules: {', '.join(changed_files)}',
            ]), ephemeral=True)
        )

    @commands.hybrid_command('update')
    @commands.is_owner()
    async def reload(self, ctx, *, modules: str):
        modules = modules.split(' ')
        cogs_reloaded = []
        module_reloaded = []

        for module in modules:
            module = 'neonbot.' + module.strip()

            if module.startswith('cogs'):
                bot.reload_extension(module)
            elif module in sys.modules:
                importlib.reload(sys.modules[module])

        await ctx.send(
            embed=Embed('\n'.join([
                'Reloaded!',
                f'Python modules: {', '.join(module_reloaded)}',
                f'Cogs modules: {', '.join(cogs_reloaded)}',
            ]), ephemeral=True)
        )

    @reload.autocomplete('modules')
    async def reload_autocomplete(self):
        return module_changed


async def setup():
    await bot.add_cog(UpdateCog())
