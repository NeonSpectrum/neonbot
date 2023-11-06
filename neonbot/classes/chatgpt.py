import asyncio

import discord
from openai import AsyncOpenAI
from discord.ext import commands
from discord.utils import find
from envparse import env
from i18n import t
import tiktoken

from neonbot.classes.embed import Embed
from neonbot.models.chatgpt import Message, Chat
from neonbot.models.server import Server
from neonbot.utils.functions import split_long_message


class ChatGPT:
    MAX_TOKEN = 4000

    def __init__(self, thread: discord.Thread):
        self.server = Server.get_instance(thread.guild.id)
        self.thread = thread
        self.chat = self.get_chat(thread.id)
        self.encoder = tiktoken.get_encoding('gpt2')
        self.client = AsyncOpenAI()

    def get_chat(self, thread_id: int):
        if chat := find(lambda chat: chat.thread_id == thread_id, self.server.chatgpt.chats):
            return chat

        self.server.chatgpt.chats.append(Chat(thread_id=thread_id, messages=[]))

        return self.get_chat(thread_id)

    def add_token(self, token: int):
        self.chat.token = self.chat.token + token if self.chat.token else token

    async def add_message(self, message: str):
        self.chat.messages.append(Message(role='user', content=message))
        self.add_token(len(self.encoder.encode(message)))

        if self.chat.token > ChatGPT.MAX_TOKEN:
            await self.trim_messages()

    async def trim_messages(self):
        saved_messages = []
        total_tokens = 0
        conversation = []
        conversation_tokens = 0

        for message in reversed(self.chat.messages):
            tokens = len(self.encoder.encode(message.content))

            conversation.insert(0, message)
            conversation_tokens += tokens

            if total_tokens + conversation_tokens > ChatGPT.MAX_TOKEN:
                break

            if message.role == 'user':
                saved_messages = conversation + saved_messages
                total_tokens += conversation_tokens
                conversation = []
                conversation_tokens = 0

        self.chat.messages.clear()
        self.chat.messages.extend(saved_messages)
        self.chat.token = total_tokens
        await self.server.save_changes()

    async def get_response(self) -> str:
        chat_completion = await self.client.chat.completions.create(
            model=env.str('OPENAI_MODEL', default='gpt-3.5-turbo'),
            messages=[{'role': message.role, 'content': message.content} for message in self.chat.messages]
        )
        answer = chat_completion.choices[0].message.content
        self.chat.messages.append(Message(role='assistant', content=answer))
        self.add_token(chat_completion.usage.total_tokens)
        await self.server.save_changes()

        return answer

    @staticmethod
    async def process_message(ctx: commands.Context):
        server = Server.get_instance(ctx.guild.id)
        channel = ctx.channel
        content = ctx.message.content

        is_channel = isinstance(channel, discord.TextChannel)
        is_thread = isinstance(channel, discord.Thread)

        if not is_channel and not is_thread:
            return False

        if is_channel and channel.id != server.channel.chatgpt:
            return False

        if is_thread and channel.parent_id != server.channel.chatgpt:
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
                chatgpt = ChatGPT(channel)
                await chatgpt.add_message(content)
                response = await chatgpt.get_response()

                for message in split_long_message(response):
                    await channel.send(message)
        finally:
            await channel.edit(locked=False)

        if chatgpt.chat.token > ChatGPT.MAX_TOKEN:
            await chatgpt.trim_messages()

        if content.lower().strip() == 'bye':
            async def remove():
                await asyncio.sleep(5)
                await channel.edit(archived=True, locked=True)

            ctx.bot.loop.create_task(remove())

        return True
