from io import BytesIO
from typing import List, Union

import google.generativeai as genai
from PIL import Image
from discord.ext import commands
from envparse import env

from neonbot.utils import log

genai.configure(api_key=env.str('GEMINI_API_KEY'))

class GeminiChat:
    def __init__(self, ctx):
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.response = None
        self.prompt = ctx.message.content[3:].strip()

    async def generate_content(self, ctx: commands.Context):
        prompts = [self.prompt]

        if len(ctx.message.attachments) > 0:
            for attachment in ctx.message.attachments:
                try:
                    attachment_data = await attachment.read()
                    image_data = BytesIO(attachment_data)
                    image = Image.open(image_data)
                    prompts.append(image)
                except (IOError, OSError):
                    pass

        self.response = await self.model.generate_content_async(prompts)

    def get_response(self):
        return self.response.text if self.response else None

    def get_prompt(self):
        return self.prompt

    def set_prompt_concise(self):
        self.prompt = 'Please provide a concise answer. ' + self.prompt