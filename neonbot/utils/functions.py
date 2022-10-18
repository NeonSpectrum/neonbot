import asyncio
from typing import Union

import discord


async def edit_message(message: Union[discord.Message, None], **kwargs) -> None:
    if message is None:
        return

    try:
        await message.edit(**kwargs)
    except discord.NotFound:
        pass


async def delete_message(*messages: Union[discord.Message, None]) -> None:
    await asyncio.gather(
        *[message.delete() for message in messages if message is not None],
        return_exceptions=True
    )


async def shell_exec(command: str) -> str:
    process = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    return stdout.decode().strip()
