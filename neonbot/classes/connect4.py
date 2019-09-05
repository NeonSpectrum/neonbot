import asyncio
import random

from .. import bot
from ..helpers.constants import CHOICES_EMOJI
from ..helpers.utils import Embed


class Connect4:
    def __init__(self, channel_id):
        self.channel = bot.get_channel(channel_id)
        self.config = bot.db.get_guild(self.channel.guild.id).config
        self.board = None
        self.players = []
        self.turn = random.randint(0, 1)
        self.last_board_message = None
        self.waiting_message = None
        self.timeout = None
        self.winner = None

    async def join(self, user):
        if user not in self.players:
            self.players.append(user)
            if len(self.players) != 2:
                self.timeout = bot.loop.create_task(self.join_timeout())
                self.waiting_message = await self.channel.send(
                    embed=Embed(
                        f"Waiting for players to join. To join the game please use `{self.config.prefix}connect4`"
                    )
                )
            else:
                self.timeout.cancel()
                self.reset_board()
                await self.show_board()
                await self.start()
        else:
            await self.channel.send(embed=Embed("You are already in the game."))

    async def start(self):
        while True:

            def check(m):
                return (
                    any(
                        x.id == m.author.id and i == self.turn
                        for i, x in enumerate(self.players)
                    )
                    and m.content.isdigit()
                    and int(m.content) > 0
                    and int(m.content) <= 7
                )

            try:
                msg = await bot.wait_for("message", check=check, timeout=30)
                is_moved = self.move_player(msg.author, int(msg.content) - 1)
                if not is_moved:
                    await self.channel.send(embed=Embed(f"{msg.content} is full."))
                    continue
                self.winner = self.check_winner()
                self.next_player()
                await self.show_board()
                if self.winner:
                    break
            except asyncio.TimeoutError:
                self.winner = self.next_player()
                await self.show_board(timeout=True)

    async def join_timeout(self):
        await asyncio.sleep(20)
        self.players = []
        await self.waiting_message.delete()
        await self.channel.send(
            embed=Embed("Insufficient players. The game will now close."),
            delete_after=5,
        )

    def next_player(self):
        self.turn = 1 if self.turn == 0 else 0
        return self.turn

    def reset_board(self):
        self.board = [
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
        ]

    async def show_board(self, timeout=False):
        winner = self.winner
        board = []

        for row in self.board:
            arr = []
            for circle in row:
                if circle == 0:
                    arr.append("⚫")
                elif circle == 1:
                    arr.append("🔴")
                elif circle == 2:
                    arr.append("🔵")
            board.append("".join(arr))
        board.append("".join(CHOICES_EMOJI[:7]))
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
        embed.description = "\n".join(board)
        embed.set_footer(
            text=f"Started by {self.players[0]}", icon_url=self.players[0].avatar_url
        )
        if self.last_board_message:
            await self.last_board_message.delete()
        self.last_board_message = await self.channel.send(embed=embed)

        if winner:
            self.__init__(self.channel.id)

    def move_player(self, user_id, index):
        for i in range(len(self.board) - 1, -1, -1):
            if self.board[i][index] == 0:
                self.board[i][index] = self.players.index(user_id) + 1
                return True
        return False

    def _check_line(self, a, b, c, d):
        return a != 0 and a == b and a == c and a == d

    def check_winner(self):
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
