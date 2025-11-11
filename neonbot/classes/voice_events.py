import discord

from neonbot.classes.embed import Embed
from neonbot.utils.functions import get_log_prefix


class VoiceEvents:
    def __init__(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        self.member = member
        self.before = before
        self.after = after

        role = self.member.guild.default_role
        self.before_readable = self.before.channel.permissions_for(role).view_channel if self.before.channel else False
        self.after_readable = self.after.channel.permissions_for(role).view_channel if self.after.channel else False

    @property
    def is_channel_changed(self):
        return self.before.channel != self.after.channel

    @property
    def is_readable(self):
        return self.before_readable and self.after_readable

    @property
    def is_self_deafen_changed(self):
        return self.is_readable and self.before.self_deaf != self.after.self_deaf

    @property
    def is_self_muted_changed(self):
        return self.is_readable and self.before.self_mute != self.after.self_mute

    @property
    def is_server_deafen_changed(self):
        return self.is_readable and self.before.deaf != self.after.deaf

    @property
    def is_server_muted_changed(self):
        return self.is_readable and self.before.mute != self.after.mute

    @property
    def is_self_stream_changed(self):
        return self.is_readable and self.before.self_stream != self.after.self_stream

    @property
    def is_self_video_changed(self):
        return self.is_readable and self.before.self_video != self.after.self_video

    def get_channel_changed_message(self):
        msg = None

        if self.after.channel and self.before.channel and self.before_readable and self.after_readable:
            msg = f'**{self.member.mention}** has moved from **{self.before.channel.mention} to {self.after.channel.mention}**'
        elif self.after.channel and self.after_readable:
            msg = f'**{self.member.mention}** has connected to **{self.after.channel.mention}**'
        elif self.before_readable:
            msg = f'**{self.member.mention}** has disconnected from **{self.before.channel.mention}**'

        if msg:
            embed = Embed(f'{get_log_prefix()}{msg}')
            return embed

        return None

    def get_self_deafen_message(self):
        if not self.before.self_deaf and self.after.self_deaf:
            msg = f'**{self.member.mention}** has deafened themselves on **{self.after.channel.mention}**'
        else:
            msg = f'**{self.member.mention}** has un-deafened themselves on **{self.after.channel.mention}**'

        return Embed(f'{get_log_prefix()}{msg}')

    def get_self_muted_message(self):
        if not self.before.self_mute and self.after.self_mute:
            msg = f'**{self.member.mention}** has muted themselves on **{self.after.channel.mention}**'
        else:
            msg = f'**{self.member.mention}** has un-muted themselves on **{self.after.channel.mention}**'

        return Embed(f'{get_log_prefix()}{msg}')

    def get_server_deafen_message(self):
        if not self.before.deaf and self.after.deaf:
            msg = f'**{self.member.mention}** has been server deafened on **{self.after.channel.mention}**'
        else:
            msg = f'**{self.member.mention}** has been server un-deafened on **{self.after.channel.mention}**'

        return Embed(f'{get_log_prefix()}{msg}')

    def get_server_muted_message(self):
        if not self.before.mute and self.after.mute:
            msg = f'**{self.member.mention}** has been server muted on **{self.after.channel.mention}**'
        else:
            msg = f'**{self.member.mention}** has been server un-muted on **{self.after.channel.mention}**'

        return Embed(f'{get_log_prefix()}{msg}')

    def get_self_stream_message(self):
        if not self.before.self_stream and self.after.self_stream:
            msg = f'**{self.member.mention}** started streaming on **{self.after.channel.mention}**'
        else:
            msg = f'**{self.member.mention}** finished streaming on **{self.after.channel.mention}**'

        return Embed(f'{get_log_prefix()}{msg}')

    def get_self_video_message(self):
        if not self.before.self_video and self.after.self_video:
            msg = f'**{self.member.mention}** opened their video on **{self.after.channel.mention}**'
        else:
            msg = f'**{self.member.mention}** closed their video on **{self.after.channel.mention}**'

        return Embed(f'{get_log_prefix()}{msg}')
