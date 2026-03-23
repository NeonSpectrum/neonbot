import inspect
from typing import List
from typing import TYPE_CHECKING

import discord
import discord.ext.commands
import google.genai as genai
from discord.ext import commands
from google.genai import types
from json_repair import repair_json

from neonbot.env import GEMINI_MODEL
from neonbot.models.guild import GuildModel
from neonbot.utils import log

if TYPE_CHECKING:
    from neonbot import NeonBot

client = genai.Client()


class GeminiChat:
    def __init__(self, ctx: commands.Context['NeonBot'], prompt: str = None):
        self.model_name = GEMINI_MODEL
        self.response = None
        self.ctx = ctx
        self.bot = ctx.bot
        self.prompt = prompt or ctx.message.content

    async def generate_content(self):
        try:
            with open('./system_instruction.md', 'r') as f:
                system_instruction = f.read()
        except FileNotFoundError:
            system_instruction = self.bot.setting.gemini_system_instruction

        system_instruction = self.replace_placeholder(system_instruction)

        contents = []

        if self.ctx.message.reference:
            messages = await self.get_all_messages()
        else:
            messages = [self.ctx.message]

        for message in messages:
            text = message.content

            if self.bot.user.mentioned_in(message):
                text = text.replace(self.bot.user.mention, self.bot.user.name).strip()

            attachments = []

            for attachment in message.attachments:
                try:
                    attachment_data = await attachment.read()
                    mime_type = attachment.content_type
                    attachments.append(types.Part.from_bytes(data=attachment_data, mime_type=mime_type))
                except (IOError, OSError):
                    pass

            contents.append(types.Content(
                role='user' if message.author.id != self.bot.user.id else 'model',
                parts=[
                    types.Part.from_text(text=text),
                    *attachments
                ]
            ))

        self.response = await client.aio.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type='application/json'
            ),

        )
        self.log()
        return self

    def log(self):
        log.info('\n'.join([
            'Gemini Chat',
            f'Question: {self.prompt}',
            f'Answer: {self.get_response()}',
            f'Commands: {self.get_json().get('commands')}'
        ]))

    def get_json(self):
        return repair_json(self.response.text, True)

    def get_response(self):
        return self.get_json().get('response')

    def get_commands(self):
        return self.get_json().get('commands', [])

    def get_command_list(self) -> List[tuple[discord.ext.commands.Command, dict]]:
        cmds = []
        data = self.get_commands()

        for row in data:
            command = self.bot.get_command(row.get('name'))
            arguments = row.get('arguments')

            sig = inspect.signature(command.callback)
            params = [p.name for p in sig.parameters.values() if p.name != 'ctx']

            args_list = []
            for param in params:
                value = arguments.get(param, None)
                if value is not None:
                    args_list.append(str(value))

            cmds.append((command, args_list))

        return cmds

    def get_prompt(self):
        return self.prompt

    async def get_all_messages(self):
        channel = self.ctx.channel
        last_message = self.ctx.message

        messages = []
        last_reference_id = last_message.id

        async for message in channel.history(limit=1000):
            if message.id == last_reference_id:
                messages.append(message)

                if message.reference:
                    last_reference_id = message.reference.message_id
                else:
                    break

        return messages[::-1]

    def replace_placeholder(self, text):
        player = self.bot.lavalink.player_manager.get(self.ctx.guild.id)
        player_settings = GuildModel.get_instance(self.ctx.guild.id)
        track_list = []

        if player:
            for track in player.playlist:
                track_list.append({'index': track.extra['index'], 'title': track.title, 'identifier': track.identifier})

        placeholders = {
            '{{DISPLAY_NAME}}': self.bot.user.name,
            '{{OWNER_ID}}': self.bot.get_user(self.bot.app_info.owner.id).id,
            '{{USER_ID}}': self.bot.get_user(self.bot.app_info.owner.id).id,
            '{{GUILD_DATA}}': self.get_guild_data(),
            '{{PLAYER_DATA}}': {
                'settings': {
                    'shuffle': player_settings.music.shuffle,
                    'autoplay': player_settings.music.autoplay,
                    'repeat': player_settings.music.repeat,
                },
                'track_list': track_list
            }
        }

        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, str(value))

        return text

    def get_guild_data(self):
        guild = self.ctx.guild

        data = {
            "id": guild.id,
            "name": guild.name,
            "owner_id": guild.owner_id,
            "channels": [{
                'id': channel.id,
                'name': channel.name,
                'connected': [member.id for member in channel.members] if isinstance(channel, discord.VoiceChannel) else [],
            } for channel in guild.channels],
            "members": [{
                "id": member.id,
                "name": member.display_name,
            } for member in guild.members],
        }

        return data
