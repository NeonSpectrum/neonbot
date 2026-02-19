import json

import google.genai as genai
from discord.ext import commands
from envparse import env
from google.genai import types

from neonbot import bot
from neonbot.utils import log

client = genai.Client()


class GeminiChat:
    def __init__(self, ctx: commands.Context):
        self.model_name = env.str('GEMINI_MODEL')
        self.response = None
        self.ctx = ctx
        self.prompt = ctx.message.content

    async def generate_content(self):
        try:
            with open('./system_instruction.md', 'r') as f:
                system_instruction = f.read()
        except FileNotFoundError:
            system_instruction = bot.setting.gemini_system_instruction

        system_instruction = self.replace_placeholder(system_instruction)

        contents = []

        if self.ctx.message.reference:
            messages = await self.get_all_messages()
        else:
            messages = [self.ctx.message]

        for message in messages:
            text = message.content

            if bot.user.mentioned_in(message):
                text = text.replace(bot.user.mention, bot.user.name).strip()

            attachments = []

            for attachment in message.attachments:
                try:
                    attachment_data = await attachment.read()
                    mime_type = attachment.content_type
                    attachments.append(types.Part.from_bytes(data=attachment_data, mime_type=mime_type))
                except (IOError, OSError):
                    pass

            contents.append(types.Content(
                role='user' if message.author.id != bot.user.id else 'model',
                parts=[
                    types.Part.from_text(text=text),
                    *attachments
                ]
            ))

        self.response = await client.aio.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        self.log()
        return self

    def log(self):
        log.info(f'Gemini Chat\nQuestion: {self.prompt}\nAnswer: {self.get_response()}')

    def get_response(self):
        return self.response.text if self.response else None

    def get_commands(self):
        try:
            cmds = []
            data = json.loads(self.get_response())

            for row in data:
                command = bot.get_command(row['name'])
                arguments = row['arguments']
                cmds.append([command, arguments])

            return cmds
        except ValueError:
            return False

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
        player = bot.lavalink.player_manager.get(self.ctx.guild.id)

        if player:
            playlist = []

            for track in player.playlist:
                playlist.append({'index': track.extra['index'], 'title': track.title, 'identifier': track.identifier})

            text = text.replace('{{PLAYER_DATA}}', json.dumps(playlist))

        text = text.replace('{{DISPLAY_NAME}}', bot.user.name)

        return text
