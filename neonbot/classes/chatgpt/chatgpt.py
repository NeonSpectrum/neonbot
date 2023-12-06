import asyncio

import discord
from openai import AsyncOpenAI
from discord.ext import commands
from discord.utils import find
from envparse import env
from i18n import t
import tiktoken

from neonbot.classes.chatgpt.chat_thread import ChatThread
from neonbot.classes.embed import Embed
from neonbot.models.chatgpt import Message, Chat
from neonbot.models.guild import Guild
from neonbot.utils.functions import split_long_message


class ChatGPT:
    def __init__(self):
        self.client = AsyncOpenAI()

    async def create_thread(self, ctx: commands.Context):
        server = Guild.get_instance(ctx.guild.id)
        channel = ctx.channel
        content = ctx.message.content

        is_channel = isinstance(channel, discord.TextChannel)
        is_thread = isinstance(channel, discord.Thread)

        if not is_channel and not is_thread:
            return False

        if is_channel and channel.id != server.chatgpt.channel_id:
            return False

        if is_thread and channel.parent_id != server.chatgpt.channel_id:
            return False

        if ctx.message.content.startswith('!!'):
            return False

        if is_channel:
            await ctx.message.delete()
            channel = await ctx.channel.create_thread(name=content[0:97] + '...' if len(content) > 100 else content)
            await channel.add_user(ctx.author)

        try:
            await channel.edit(locked=True)

            async with channel.typing():
                chat_thread = ChatThread(self.client, channel)
                await chat_thread.add_message(content)
                response = await chat_thread.get_response()

                for message in split_long_message(response):
                    await channel.send(message)
        finally:
            await channel.edit(locked=False)

        if chat_thread.chat.token > ChatThread.MAX_TOKEN:
            await chat_thread.trim_messages()

        if content.lower().strip() == 'bye':
            async def remove():
                await asyncio.sleep(5)
                await channel.edit(archived=True, locked=True)

            ctx.bot.loop.create_task(remove())

        return True

    def generate_image(self, keyword):
        return self.client.images.generate(
            model=env.str('OPENAI_IMAGE_MODEL', default='dall-e-2'),
            prompt=keyword,
            n=1,
            size='1024x1024',
            quality="standard",
        )
