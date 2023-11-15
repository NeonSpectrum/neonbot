from typing import Union, List

import discord


class SelectChoices(discord.ui.Select):
    def __init__(self, placeholder, options: Union[List[str], List[dict]]):
        super().__init__(
            placeholder=placeholder,
            options=[discord.SelectOption(**{'label': option} if isinstance(option, str) else option)
                     for option in options]
        )
