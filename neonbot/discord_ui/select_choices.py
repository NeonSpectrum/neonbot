from typing import List, Union

import discord


class SelectChoices(discord.ui.Select):
    def __init__(self, placeholder, options: Union[List[str], List[dict]]):
        super().__init__(
            min_values=1,
            max_values=len(options),
            placeholder=placeholder,
            options=[
                discord.SelectOption(**{'label': option} if isinstance(option, str) else option) for option in options
            ],
        )
