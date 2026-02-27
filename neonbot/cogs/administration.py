import asyncio
import contextlib
import sys
from io import StringIO
from typing import Generator, Optional
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View

from neonbot.classes.discord.embed import Embed
from neonbot.classes.discord.select_choices import SelectChoices
from neonbot.env import OWNER_GUILD_IDS
from neonbot.models.guild import GuildModel
from neonbot.utils.constants import ICONS

if TYPE_CHECKING:
    from neonbot import NeonBot


@contextlib.contextmanager
def stdout_io() -> Generator[StringIO, None, None]:
    old = sys.stdout
    stdout = StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old


class Administration(commands.Cog):
    """Administration commands that handles the management of the bot"""

    server = app_commands.Group(
        name='server',
        description='Configure the settings of the bot for this server.',
        default_permissions=discord.Permissions(administrator=True),
        guild_only=True,
    )

    settings = app_commands.Group(
        name='bot',
        description='Configure the settings of the bot globally.',
        default_permissions=discord.Permissions(administrator=True),
        guild_ids=OWNER_GUILD_IDS,
        guild_only=True,
    )

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def eval(self, ctx: commands.Context['NeonBot'], *, code: str) -> None:
        """Evaluates a line/s of python code. *BOT_OWNER"""

        variables = {'bot': self.bot, 'ctx': ctx, 'player': self.bot.lavalink.player_manager.get(ctx.guild.id), 'Embed': Embed}

        if code.startswith('```') and code.endswith('```'):
            code = '\n'.join(code.splitlines()[1:-1])

        try:
            lines = '\n'.join([f'  {i}' for i in code.splitlines()])

            with stdout_io() as s:
                exec(f'async def x():\n{lines}\n', variables)
                await discord.utils.maybe_coroutine(eval, 'x()', variables)
            output = s.getvalue()
        except Exception as e:
            output = str(e)
            await ctx.message.add_reaction('❌')
        else:
            await ctx.message.add_reaction('👌')

        if output:
            msg_array = [output[i: i + 1900] for i in range(0, len(output), 1900)]

            messages = ['```py\n' + msg.strip('\n') + '```' for msg in msg_array]
            for message in messages:
                await ctx.send(message)

    @app_commands.command(name='prune')
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def prune(
        self,
        interaction: discord.Interaction['NeonBot'],
        count: app_commands.Range[int, 1, 1000],
        member: Optional[discord.Member] = None,
    ) -> None:
        """Deletes a number of messages of a specific member (if specified). *MANAGE_MESSAGES"""

        await interaction.response.defer()

        async for message in interaction.channel.history(limit=1000 if member else count):
            if count <= 0:
                break

            if not member or message.author == member:
                await self.bot.delete_message(message)
                count -= 1

        await interaction.delete_original_response()

    @server.command(name='set-prefix')
    async def prefix(self, interaction: discord.Interaction['NeonBot'], prefix: str) -> None:
        """Sets the prefix of the current server. *ADMINISTRATOR"""

        server = GuildModel.get_instance(interaction.guild.id)
        server.prefix = prefix

        await server.save_changes(False)

        await interaction.response.send_message(
            embed=Embed(f'Prefix is now set to `{server.prefix}`.')
        )

    @settings.command(name='set-status')
    async def set_status(self, interaction: discord.Interaction['NeonBot'], status: discord.Status) -> None:
        """Sets the status of the bot. *BOT_OWNER"""

        if not status:
            return

        self.bot.setting.status = str(status)
        await self.bot.setting.save_changes(False)

        await self.bot.update_presence()

        await interaction.response.send_message(
            embed=Embed(f'Status is now set to {self.bot.settings.get("status")}.')
        )

    @settings.command(name='set-presence')
    async def set_presence(
        self,
        interaction: discord.Interaction['NeonBot'],
        presence_type: discord.ActivityType,
        name: str,
    ) -> None:
        """Sets the presence of the bot. *BOT_OWNER"""

        # noinspection PyUnresolvedReferences
        self.bot.setting.activity_type = presence_type.name
        self.bot.setting.activity_name = name

        await self.bot.setting.save_changes(False)

        await self.bot.update_presence()

        # noinspection PyUnresolvedReferences
        await interaction.response.send_message(
            embed=Embed(f'Presence is now set to **{presence_type.name} {name}**.')
        )

    @server.command(name='set-logs')
    async def set_logs(self, interaction: discord.Interaction['NeonBot'], channel: discord.TextChannel, enable: bool):
        """Sets the log channel. *ADMINISTRATOR"""

        guild = GuildModel.get_instance(interaction.guild_id)
        select = SelectChoices(
            'Select log type...',
            [
                'connect',
                'mute',
                'deafen',
                'server_deafen',
                'server_mute',
                'status',
                'activity',
                'stream',
                'video',
            ],
        )

        async def callback(_):
            for value in select.values:
                setattr(guild.channel_log, value, channel.id if enable else None)

            await guild.save_changes(False)

            await interaction.edit_original_response(
                embed=Embed(f'Log channel type `{", ".join(select.values)}` has been set to {channel.mention}'),
                view=None,
            )

        select.callback = callback

        view = View()
        view.add_item(select)

        await interaction.response.send_message(view=view, ephemeral=True)

    @server.command(name='get-logs')
    async def get_logs(self, interaction: discord.Interaction['NeonBot']):
        """Gets the log channels. *ADMINISTRATOR"""

        guild = GuildModel.get_instance(interaction.guild_id)

        embed = Embed()
        embed.set_author('Log Channels', icon_url=self.bot.user.display_avatar)

        for name, channel_id in guild.channel_log.model_dump().items():
            channel = self.bot.get_channel(channel_id or -1)
            embed.add_field(name.title().replace('_', ''), channel.mention if channel else 'None', inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @server.command(name='set-chatgpt')
    async def set_chatgpt(self, interaction: discord.Interaction['NeonBot'], channel: discord.TextChannel, enable: bool):
        """Sets the chatgpt channel. *ADMINISTRATOR"""

        guild = GuildModel.get_instance(interaction.guild_id)
        guild.chatgpt.channel_id = channel.id if enable else None
        await guild.save_changes(False)

        if guild.chatgpt.channel_id:
            await interaction.response.send_message(
                embed=Embed(f'ChatGPT is now set to {channel.mention}.')
            )

            embed = Embed()
            embed.set_author('OpenAI - ChatGPT', url='https://chat.openai.com', icon_url=ICONS['openai'])
            embed.set_description('Start a conversation with ChatGPT by asking a question in this space.')

            await channel.send(embed=embed)
        else:
            await interaction.response.send_message(
                embed=Embed('ChatGPT is now disabled.')
            )

    @settings.command(name='set-gemini-instruction')
    async def set_gemini_instruction(self, interaction: discord.Interaction['NeonBot'], value: str):
        """Sets the chatgpt channel. *ADMINISTRATOR"""

        self.bot.setting.gemini_system_instruction = value

        await self.bot.setting.save_changes(False)

        # noinspection PyUnresolvedReferences
        await interaction.response.send_message(
            embed=Embed(f'Gemini instruction is now set to **{value}**.')
        )

    @app_commands.command(name='sync')
    @app_commands.allowed_installs(guilds=False, users=True)
    @app_commands.allowed_contexts(guilds=False, dms=True, private_channels=False)
    async def sync(self, interaction: discord.Interaction['NeonBot']):
        if not self.bot.is_owner(interaction.user):
            await interaction.response.send_message(embed=Embed('No permission.'))
            return

        await self.bot.sync_command()

        guilds = [guild async for guild in self.bot.fetch_guilds()]

        await asyncio.gather(*[self.bot.sync_command(guild) for guild in guilds])

        await interaction.response.send_message(embed=Embed('Commands Synced!'))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Administration(bot))
