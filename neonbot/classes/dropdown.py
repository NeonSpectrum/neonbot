import discord


class Dropdown(discord.ui.Select):
    def __init__(self):
        # Set the options that will be presented inside the dropdown
        options = [
            discord.SelectOption(label='Moderation',
                                 description='Moderation commands to help moderate server efficiently',
                                 ),
            discord.SelectOption(label='Utility', description='Utility commands for various uses'),
            discord.SelectOption(label='Fun', description='Fun commands for chilling and hanging out in the server',
                                 ),
        ]

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder='Choose command type...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # Use the interaction object to send a response message containing
        # the user's favourite colour or choice. The self object refers to the
        # Select object, and the values attribute gets a list of the user's
        # selected options. We only want the first one.
        # await interaction.response.send_message(f'Your favourite colour is {self.values[0]}')
        await interaction.response.send_message("something here")
