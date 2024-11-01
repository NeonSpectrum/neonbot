from io import BytesIO

import discord
import google.generativeai as genai
from PIL import Image
from discord.ext import commands
from envparse import env

from neonbot.utils import log

genai.configure(api_key=env.str('GEMINI_API_KEY'))

class GeminiChat:
    def __init__(self, message):
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.response = None
        self.prompt = message.lstrip('? ')

    async def generate_content_from_ctx(self, ctx: commands.Context):
        prompts = []
        attachments = []

        # Check for message reference
        if ctx.message.reference:
            reply_to_message_id = ctx.message.reference.message_id

            try:
                replied_message = await ctx.message.channel.fetch_message(reply_to_message_id)

                prompts.append(replied_message.content)
                attachments += replied_message.attachments
            except discord.NotFound:
                pass

        # Add current message contents
        prompts.append(self.prompt)
        attachments += ctx.message.attachments

        if len(attachments) > 0:
            for attachment in attachments:
                try:
                    attachment_data = await attachment.read()
                    image_data = BytesIO(attachment_data)
                    image = Image.open(image_data)
                    prompts.append(image)
                except (IOError, OSError):
                    pass

        self.response = await self.model.generate_content_async(prompts)
        self.log()
        return self

    async def generate_content(self):
        self.response = await self.model.generate_content_async([self.prompt])
        self.log()
        return self

    def log(self):
        log.info(f"Gemini Chat\nQuestion: {self.prompt}\nAnswer: {self.get_response()}")

    def get_response(self):
        return self.response.text if self.response else None

    def get_prompt(self):
        return self.prompt

    def set_prompt_concise(self):
        self.prompt = 'Please provide a concise answer. ' + self.prompt

    @staticmethod
    async def generate(prompt):
        gemini_chat = await GeminiChat(prompt).generate_content()
        return gemini_chat.get_response()
