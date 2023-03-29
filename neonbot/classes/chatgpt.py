import discord
import openai
from discord.ext import commands
from discord.utils import find

from neonbot.models.chatgpt import Message, Chat
from neonbot.models.server import Server
from neonbot.utils.functions import split_long_message


class ChatGPT:
    def __init__(self, thread: discord.Thread):
        self.server = Server.get_instance(thread.guild.id)
        self.thread = thread
        self.chat = self.get_chat(thread.id)

    def get_chat(self, thread_id: int):
        if chat := find(lambda chat: chat.thread_id == thread_id, self.server.chatgpt.chats):
            return chat

        self.server.chatgpt.chats.append(Chat(thread_id=thread_id, messages=[]))

        return self.get_chat(thread_id)

    def add_message(self, message: str):
        self.chat.messages.append(Message(role='user', content=message))

    async def get_response(self) -> str:
        chat_completion = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{'role': message.role, 'content': message.content} for message in self.chat.messages]
        )
        answer = chat_completion.choices[0].message.content
        self.chat.messages.append(Message(role='assistant', content=answer))
        await self.server.save_changes()

        return answer

    @staticmethod
    async def process_message(ctx: commands.Context):
        server = Server.get_instance(ctx.guild.id)
        channel = ctx.channel

        if isinstance(channel, discord.TextChannel) and channel.id != server.channel.chatgpt:
            return False

        if isinstance(channel, discord.Thread) and channel.parent_id != server.channel.chatgpt:
            return False

        if isinstance(ctx.channel, discord.TextChannel):
            channel = await ctx.message.create_thread(name=ctx.message.content)
            await channel.add_user(ctx.author)

        async with channel.typing():
            chatgpt = ChatGPT(channel)
            chatgpt.add_message(ctx.message.content)
            response = await chatgpt.get_response()

            for message in split_long_message(response):
                await channel.send(message)

        return True
