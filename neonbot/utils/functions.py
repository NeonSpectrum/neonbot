import asyncio

import discord


async def shell_exec(command: str) -> str:
    process = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    return stdout.decode().strip()


def get_command_string(interaction: discord.Interaction):
    params = ' '.join([
        f'{key}="{value}"'
        for key, value in interaction.namespace.__dict__.items()
    ])

    return f"/{interaction.command.name} {params}"
