import asyncio
import random
from typing import List

import discord

from .. import bot
from ..helpers.constants import CHOICES_EMOJI
from ..helpers.utils import Embed


class Connect4:
    """
    Initializes a connect 4 game that can start, stop, and show scoreboard.
    Available to only one game in a channel.
    """

    def __init__(self, channel: discord.TextChannel):
        self.channel = bot.get_channel(channel.id)
        self.config = bot.db.get_guild(self.channel.guild.id).config

        self.reset()

    def reset(self) -> None:
        self.board: list = []
        self.players: List[discord.User] = []
        self.turn = random.randint(0, 1)
        self.last_board_message: discord.Message = None
        self.waiting_message: discord.Message = None
        self.timeout: asyncio.Task

        self.reset_board()

    async def join(self, user: discord.User) -> None:
        """Join the game and determine if the game will start or not

        Parameters
        ----------
        user : discord.User
        """
        if user not in self.players:
            self.players.append(user)
            if len(self.players) != 2:
                self.timeout = bot.loop.create_task(self.join_timeout())
                self.waiting_message = await self.channel.send(
                    embed=Embed(
                        f"Waiting for players to join. To join the game please use`{self.config.prefix}connect4`"
                    )
                )
            else:
                self.timeout.cancel()
                await self.show_board()
                await self.start()
        else:
            await self.channel.send(embed=Embed("You are already in the game."))

    async def start(self) -> None:
        """Starts the game and will loop until winner is detected"""

        def check(m: discord.Message) -> bool:
            return (
                m.content.isdigit()
                and any(
                    x.id == m.author.id and i == self.turn
                    for i, x in enumerate(self.players)
                )
                and int(m.content) > 0
                and int(m.content) <= 7
            )

        try:
            msg = await bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            self.winner = self.next_player()
            await self.show_board(timeout=True)
        else:
            is_moved = self.move_player(msg.author, int(msg.content) - 1)
            if not is_moved:
                await self.channel.send(embed=Embed(f"{msg.content} is full."))
                self.start()
                return
            self.winner = self.check_winner()
            self.next_player()
            await self.show_board()
            if not self.winner:
                self.start()

    async def join_timeout(self) -> None:
        """Add timeout to check whether a player will join the game or not."""

        await asyncio.sleep(20)
        self.players = []
        asyncio.gather(
            self.waiting_message.delete(),
            self.channel.send(
                embed=Embed("Insufficient players. The game will now close."),
                delete_after=5,
            ),
        )

    def next_player(self) -> int:
        self.turn = 1 if self.turn == 0 else 0
        return self.turn

    def reset_board(self) -> None:
        self.board = [
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
        ]

    async def show_board(self, timeout: bool = False) -> None:
        """Shows the connect4 board and displays the current player turn or the winner.

        Parameters
        ----------
        timeout : bool, optional
            To check if the winner win through timeout, by default False
        """

        winner = self.winner
        board = []

        for row in self.board:
            line = [("⚫", "🔴", "🔵")[circle] for circle in row]
            board.append(line)
        board.append(CHOICES_EMOJI[:7])

        if not winner:
            embed = Embed(title=f"Player to move: **{self.players[self.turn]}**")
        elif winner == -1:
            embed = Embed(title="Congratulations.\nIt's a draw!")
        else:
            embed = Embed(
                title=f"Congratulations.\n**{self.players[winner-1]}** won the game!"
            )
            if timeout:
                other_player = 1 if winner == 0 else 0
                embed.title = (
                    f"**{self.players[other_player-1]}** didn't answer.\n" + embed.title
                )
        embed.description = "\n".join(["".join(b) for b in board])
        embed.set_footer(
            text=f"Started by {self.players[0]}", icon_url=self.players[0].avatar_url
        )

        if self.last_board_message:
            await self.last_board_message.delete()
        self.last_board_message = await self.channel.send(embed=embed)

        if winner:
            self.reset()

    def move_player(self, user: discord.User, index: int) -> bool:
        """Moves the player and check if the slot is full

        Parameters
        ----------
        user : discord.User
        index : int
            Location to where the player moves

        Returns
        -------
        bool
            Can move or not?
        """
        for i in range(len(self.board) - 1, -1, -1):
            if self.board[i][index] == 0:
                self.board[i][index] = self.players.index(user) + 1
                return True
        return False

    def _check_line(self, a: int, b: int, c: int, d: int) -> bool:
        return a != 0 and a == b and a == c and a == d

    def check_winner(self) -> int:
        """Get winner by checking lines horizontally and verically

        Returns
        -------
        int
            -1 = Draw
            0 = No Winner
            [1, 2] = Winner
        """
        board = self.board

        for i in range(0, 3):
            for j in range(0, 7):
                if self._check_line(
                    board[i][j], board[i + 1][j], board[i + 2][j], board[i + 3][j]
                ):
                    return board[i][j]

        # Check right
        for i in range(0, 6):
            for j in range(0, 4):
                if self._check_line(
                    board[i][j], board[i][j + 1], board[i][j + 2], board[i][j + 3]
                ):
                    return board[i][j]

        # Check down-right
        for i in range(0, 3):
            for j in range(0, 4):
                if self._check_line(
                    board[i][j],
                    board[i + 1][j + 1],
                    board[i + 2][j + 2],
                    board[i + 3][j + 3],
                ):
                    return board[i][j]

        # Check down-left
        for i in range(0, 6):
            for j in range(0, 4):
                if self._check_line(
                    board[i][j],
                    board[i - 1][j + 1],
                    board[i - 2][j + 2],
                    board[i - 3][j + 3],
                ):
                    return board[i][j]

        # Check if draw
        for i in range(0, 6):
            for j in range(0, 7):
                if board[i][j] == 0:
                    return board[i][j]

        return -1
