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
from i18n import t

from neonbot.discord_ui.embed import Embed
from neonbot.discord_ui.select_choices import SelectChoices
from neonbot.env import OWNER_GUILD_IDS
from neonbot.models.guild import GuildModel

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

    def __init__(self, bot: 'NeonBot'):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def eval(self, ctx: commands.Context['NeonBot'], *, code: str) -> None:
        """Evaluates a line/s of python code. *BOT_OWNER"""

        variables = {'bot': self.bot, 'ctx': ctx, 'player': self.bot.get_player_instance(ctx.guild.id), 'Embed': Embed}

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
            embed=Embed(t('administration.prefix_set', prefix=server.prefix))
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
            embed=Embed(t('administration.status_set', status=self.bot.setting.get("status")))
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
            embed=Embed(t('administration.presence_set', type=presence_type.name, name=name))
        )

    @server.command(name='set-logs')
    async def set_logs(self, interaction: discord.Interaction['NeonBot'], channel: discord.TextChannel, enable: bool):
        """Sets the log channel. *ADMINISTRATOR"""

        guild = GuildModel.get_instance(interaction.guild_id)
        select = SelectChoices(
            t('administration.select_log_type'),
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
                embed=Embed(t('administration.log_channel_set', type=", ".join(select.values), channel=channel.mention)),
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
        embed.set_author(t('administration.log_channels_title'), icon_url=self.bot.user.display_avatar.url)

        for name, channel_id in guild.channel_log.model_dump().items():
            channel = self.bot.get_channel(channel_id or -1)
            embed.add_field(name.title().replace('_', ''), channel.mention if channel else t('administration.none'), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


    @server.command(name='set-autojoin')
    async def set_autojoin(self, interaction: discord.Interaction['NeonBot'], channel: Optional[discord.VoiceChannel] = None):
        """Sets the autojoin voice channel. *ADMINISTRATOR"""

        guild = GuildModel.get_instance(interaction.guild_id)
        guild.music.autojoin_channel_id = channel.id if channel else None
        await guild.save_changes(False)

        if channel:
            player = await self.bot.create_player_instance(interaction.guild_id)
            await player.connect(channel)

        channel_mention = channel.mention if channel else t('administration.none')
        await interaction.response.send_message(
            embed=Embed(t('administration.autojoin_set', channel=channel_mention))
        )

    @server.command(name='set-music-channel')
    async def set_music_channel(self, interaction: discord.Interaction['NeonBot'], channel: Optional[discord.VoiceChannel] = None):
        """Sets the music channel. *ADMINISTRATOR"""

        guild = GuildModel.get_instance(interaction.guild_id)
        guild.music.channel_id = channel.id if channel else None
        await guild.save_changes(False)

        channel_mention = channel.mention if channel else t('administration.none')
        await interaction.response.send_message(
            embed=Embed(t('administration.music_channel_set', channel=channel_mention))
        )

    @settings.command(name='set-gemini-instruction')
    async def set_gemini_instruction(self, interaction: discord.Interaction['NeonBot'], value: str):
        """Sets the Gemini system instruction. *ADMINISTRATOR"""

        self.bot.setting.gemini_system_instruction = value

        await self.bot.setting.save_changes(False)

        # noinspection PyUnresolvedReferences
        await interaction.response.send_message(
            embed=Embed(t('administration.gemini_instruction_set', value=value))
        )

    @app_commands.command(name='sync')
    @app_commands.allowed_installs(guilds=False, users=True)
    @app_commands.allowed_contexts(guilds=False, dms=True, private_channels=False)
    async def sync(self, interaction: discord.Interaction['NeonBot']):
        if not self.bot.is_owner(interaction.user):
            await interaction.response.send_message(embed=Embed(t('common.no_permission')))
            return

        await self.bot.sync_command()

        guilds = [guild async for guild in self.bot.fetch_guilds()]

        await asyncio.gather(*[self.bot.sync_command(guild) for guild in guilds])

        await interaction.response.send_message(embed=Embed(t('common.commands_synced')))


async def setup(bot: 'NeonBot') -> None:
    await bot.add_cog(Administration(bot))
