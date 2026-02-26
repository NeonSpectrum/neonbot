import asyncio
from typing import TYPE_CHECKING

import discord
from i18n import t

from neonbot.classes.discord.embed import Embed
from neonbot.classes.discord.view import Button, View
from neonbot.enums import Repeat
from neonbot.utils import log

if TYPE_CHECKING:
    from neonbot import NeonBot


class PlayerControls:
    def __init__(self, bot: 'NeonBot', guild_id):
        self.bot = bot
        self.guild_id = guild_id
        self.view = None

    @property
    def player(self):
        return self.bot.lavalink.player_manager.get(self.guild_id)

    def update_buttons(self, views):
        # ["🔀","⏮️","⏸️","⏭️","🔁"]

        if self.player.shuffle:
            views[0].style = discord.ButtonStyle.primary
        else:
            views[0].style = discord.ButtonStyle.secondary

        views[1].disabled = not (0 <= self.player.current_queue - 1 < len(self.player.track_list))

        if self.player.is_playing and not self.player.paused:
            views[2].emoji = '⏸️'
        else:
            views[2].emoji = '▶️'

        views[2].disabled = (
            not self.player.is_playing
            and not self.player.paused
            and self.player.loop == Repeat.OFF
            and not self.player.shuffle
            and not self.player.autoplay
        )

        views[3].disabled = (
            (not self.player.is_playing or self.player.is_last_track)
            and self.player.loop == Repeat.OFF
            and not self.player.autoplay
            and not self.player.shuffle
        )

        if self.player.loop == Repeat.OFF:
            views[4].emoji = '🔁'
            views[4].style = discord.ButtonStyle.secondary
        elif self.player.loop == Repeat.SINGLE:
            views[4].emoji = '🔂'
            views[4].style = discord.ButtonStyle.primary
        elif self.player.loop == Repeat.ALL:
            views[4].emoji = '🔁'
            views[4].style = discord.ButtonStyle.primary

        if self.player.autoplay:
            views[5].style = discord.ButtonStyle.primary
        else:
            views[5].style = discord.ButtonStyle.secondary

        return views

    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction['NeonBot']):
        async def send_message(message):
            await interaction.channel.send(embed=Embed(message))
            message = message.replace(interaction.user.mention, str(interaction.user))
            log.cmd(interaction, message)

        if not interaction.user.voice or (
            interaction.user.voice and interaction.user.voice.channel != self.player.ctx.voice_client.channel
        ):
            if not await self.bot.is_owner(interaction.user):
                await self.bot.send_response(interaction, embed=Embed(t('music.cannot_interact')), ephemeral=True)
                return

        tasks = []

        if button.emoji.name == '▶️':  # play
            if self.player.paused:
                tasks.append(self.player.resume(requester=interaction.user))
            else:
                tasks.append(self.player.play_next())
        elif button.emoji.name == '⏸️':  # pause
            tasks.append(self.player.pause(requester=interaction.user))
        elif button.emoji.name == '⏮️':  # prev
            tasks.append(send_message(t('music.player_controls_pressed', action='back', user=interaction.user.mention)))
            tasks.append(self.player.prev())
        elif button.emoji.name == '⏭️':  # next
            tasks.append(send_message(t('music.player_controls_pressed', action='next', user=interaction.user.mention)))
            tasks.append(self.player.next())
        elif button.emoji.name in ('🔁', '🔂'):  # repeat
            modes = [Repeat.OFF, Repeat.SINGLE, Repeat.ALL]
            index = (modes.index(Repeat(self.player.loop)) + 1) % 3
            mode = modes[index]

            tasks.append(send_message(t('music.repeat_changed', mode=mode.name.lower(), user=interaction.user.mention)))
            self.player.set_loop(mode.value)
        elif button.emoji.name == '🔀':  # shuffle
            state = not self.player.shuffle

            tasks.append(send_message(t('music.shuffle_changed', mode='on' if state else 'off', user=interaction.user.mention)))
            self.player.set_shuffle(state)
        elif button.emoji.name == '♾️':  # autoplay
            state = not self.player.autoplay

            tasks.append(send_message(t('music.autoplay_changed', mode='on' if state else 'off', user=interaction.user.mention)))
            self.player.set_autoplay(state)
        elif button.emoji.name == '⏏️':  # reset
            tasks.append(send_message(t('music.player_controls_pressed', action='reset', user=interaction.user.mention)))
            tasks.append(self.player.reset())

        await asyncio.gather(*tasks)

    def initialize(self) -> None:
        buttons = [
            Button(emoji='🔀'),
            Button(emoji='⏮️', style=discord.ButtonStyle.primary),
            Button(emoji='⏸️', style=discord.ButtonStyle.primary),
            Button(emoji='⏭️', style=discord.ButtonStyle.primary),
            Button(emoji='🔁'),
            Button(emoji='♾️', label='Autoplay'),
            Button(emoji='⏏️', label='Reset'),
        ]
        self.update_buttons(buttons)

        def callback(*args, **kwargs):
            self.bot.loop.create_task(self.callback(*args, **kwargs))

        self.view = View.create_button(buttons, callback, timeout=None)

    def get(self) -> View:
        self.refresh()

        return self.view

    def refresh(self) -> None:
        if not self.view:
            return

        views = self.view.children
        self.view.clear_items()

        for button in self.update_buttons(views):
            self.view.add_item(button)
