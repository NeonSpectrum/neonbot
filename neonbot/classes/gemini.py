from io import BytesIO

import discord
import google.genai as genai
from PIL import Image
from discord.ext import commands
from envparse import env
from google.genai import types

from neonbot import bot
from neonbot.utils import log

client = genai.Client()

class GeminiChat:
    def __init__(self, message):
        self.model_name = env.str('GEMINI_MODEL')
        self.response = None
        self.prompt = message

    async def generate_content_from_ctx(self, ctx: commands.Context):
        contents = []

        if ctx.message.reference:
            messages = await get_all_descendants(ctx.channel, ctx.message.id)
        else:
            messages = [ctx.message]

        for message in message:
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
                    types.Part.from_text(message.content),
                    *attachments
                ]
            ))

        self.response = await client.aio.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=bot.setting.gemini_system_instruction
            )
        )
        self.log()
        return self

    async def generate_content(self):
        self.response = await client.aio.models.generate_content(
            model=self.model_name,
            contents=[self.prompt],
            config=types.GenerateContentConfig(
                system_instruction=bot.setting.gemini_system_instruction
            )
        )
        self.log()
        return self

    def log(self):
        log.info(f'Gemini Chat\nQuestion: {self.prompt}\nAnswer: {self.get_response()}')

    def get_response(self):
        return self.response.text if self.response else None

    def get_prompt(self):
        return self.prompt

    def set_prompt_concise(self):
        self.prompt = 'Please provide a concise answer. ' + self.prompt

    @staticmethod
    async def generate(prompt, precise=False):
        gemini_chat = GeminiChat(prompt)
        if precise:
            gemini_chat.set_prompt_concise()
        await gemini_chat.generate_content()
        return gemini_chat.get_response()

    async def get_all_descendants(channel, last_message_id, limit=1000):
        descendants = []
        current_ids = {last_message_id}
        async for msg in channel.history(limit=limit):  # Newest-first, skips unrelated
            if msg.reference and msg.reference.message_id in current_ids:
                descendants.append(msg)
                current_ids.add(msg.id)  # Enables nested like C → B
            elif msg.id == last_message_id:
                break
        return sorted(descendants, key=lambda m: m.created_at)  # Chrono order
