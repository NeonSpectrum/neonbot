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
        prompts = []
        attachments = []

        if ctx.message.reference:
            reply_to_message_id = ctx.message.reference.message_id

            try:
                replied_message = await ctx.message.channel.fetch_message(reply_to_message_id)
                prompts.append(replied_message.content)
                attachments += replied_message.attachments
            except discord.NotFound:
                pass

        prompts.append(self.prompt)
        attachments += ctx.message.attachments

        contents = [self.prompt]

        if len(attachments) > 0:
            for attachment in attachments:
                try:
                    attachment_data = await attachment.read()
                    image_data = BytesIO(attachment_data)
                    image = Image.open(image_data)
                    contents.append(image)
                except (IOError, OSError):
                    pass

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
