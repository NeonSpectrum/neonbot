import asyncio
from datetime import timedelta
from typing import Union

import discord


async def shell_exec(command: str) -> str:
    process = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    return stdout.decode().strip()


def get_command_string(interaction: discord.Interaction):
    params = []

    # Context menu starts with uppercase
    if interaction.command.name[0].isupper():
        try:
            users = list(interaction.data['resolved']['users'].values())
            params = [f"{user['username']}#{user['discriminator']}" for user in users]
        except IndexError:
            pass
    else:
        params = [
            f'{key}="{value}"'
            for key, value in interaction.namespace.__dict__.items()
        ]

    return f"{interaction.command.name} {' '.join(params)}"


def format_seconds(secs: Union[int, float]) -> str:
    formatted = str(timedelta(seconds=secs)).split(".")[0]
    if formatted.startswith("0:"):
        return formatted[2:]
    return formatted


def split_long_message(message: str):
    if len(message) < 1900:
        return [message]

    lines = message.split('\n')
    messages = []
    message = []

    for index, line in enumerate(lines):
        message.append(line)

        if len('\n'.join(message)) > 1900:
            message.pop()
            messages.append('\n'.join(message))
            message = [line]

        if index == len(lines) - 1:
            messages.append('\n'.join(message))

    return messages
