"""
中国象棋棋盘和游戏规则实现模块。

提供：
- Move: 走法（起点 → 终点）
- Board: 棋盘数据结构
- GameState: 游戏状态机（不可变设计）
"""

import copy
from .cctypes import Player, Point, Piece, PieceType
from .ccmoves import get_piece_moves

__all__ = ["Board", "GameState", "Move"]


class Move:
    """走法：从 from_point 移动到 to_point。"""

    def __init__(self, from_point, to_point):
        self.from_point = from_point
        self.to_point = to_point

    def __str__(self):
        return (f"({self.from_point.row},{self.from_point.col})"
                f"->({self.to_point.row},{self.to_point.col})")

    def __eq__(self, other):
        return (isinstance(other, Move)
                and self.from_point == other.from_point
                and self.to_point == other.to_point)

    def __hash__(self):
        return hash((self.from_point, self.to_point))


class Board:
    """
    9×10 中国象棋棋盘。
    使用字典存储: Point -> Piece，空位不存键。
    """
    NUM_ROWS = 10
    NUM_COLS = 9

    def __init__(self):
        self._grid = {}  # Point -> Piece

    def place_piece(self, point, piece):
        self._grid[point] = piece

    def remove_piece(self, point):
        return self._grid.pop(point, None)

    def get(self, point):
        return self._grid.get(point)

    def pieces_for_player(self, player):
        return [(pt, pc) for pt, pc in self._grid.items() if pc.player == player]

    def find_general(self, player):
        for pt, pc in self._grid.items():
            if pc.player == player and pc.piece_type == PieceType.GENERAL:
                return pt
        return None

    def generals_facing(self):
        """将帅对面检测：同列且中间无子则返回 True。"""
        red_gen = self.find_general(Player.red)
        black_gen = self.find_general(Player.black)
        if red_gen is None or black_gen is None:
            return False
        if red_gen.col != black_gen.col:
            return False
        min_row = min(red_gen.row, black_gen.row)
        max_row = max(red_gen.row, black_gen.row)
        for r in range(min_row + 1, max_row):
            if self.get(Point(r, red_gen.col)) is not None:
                return False
        return True

    def __deepcopy__(self, memodict=None):
        copied = Board()
        copied._grid = dict(self._grid)
        return copied

    @classmethod
    def initial_position(cls):
        """标准开局布局。"""
        board = cls()
        back = [PieceType.CHARIOT, PieceType.HORSE, PieceType.ELEPHANT,
                PieceType.ADVISOR, PieceType.GENERAL, PieceType.ADVISOR,
                PieceType.ELEPHANT, PieceType.HORSE, PieceType.CHARIOT]
        # 红方
        for col, pt in enumerate(back):
            board.place_piece(Point(0, col), Piece(Player.red, pt))
        board.place_piece(Point(2, 1), Piece(Player.red, PieceType.CANNON))
        board.place_piece(Point(2, 7), Piece(Player.red, PieceType.CANNON))
        for col in (0, 2, 4, 6, 8):
            board.place_piece(Point(3, col), Piece(Player.red, PieceType.PAWN))
        # 黑方
        for col, pt in enumerate(back):
            board.place_piece(Point(9, col), Piece(Player.black, pt))
        board.place_piece(Point(7, 1), Piece(Player.black, PieceType.CANNON))
        board.place_piece(Point(7, 7), Piece(Player.black, PieceType.CANNON))
        for col in (0, 2, 4, 6, 8):
            board.place_piece(Point(6, col), Piece(Player.black, PieceType.PAWN))
        return board


# ── PLACEHOLDER_GAMESTATE ──


class GameState:
    """
    游戏状态（不可变设计）。每次走子返回新状态。
    """

    def __init__(self, board, next_player, previous_state, last_move):
        self.board = board
        self.next_player = next_player
        self.previous_state = previous_state
        self.last_move = last_move

    @classmethod
    def new_game(cls):
        return cls(Board.initial_position(), Player.red, None, None)

    def apply_move(self, move):
        next_board = copy.deepcopy(self.board)
        piece = next_board.remove_piece(move.from_point)
        next_board.remove_piece(move.to_point)  # 吃子（如有）
        next_board.place_piece(move.to_point, piece)
        return GameState(next_board, self.next_player.other, self, move)

    def legal_moves(self):
        moves = []
        for point, piece in self.board.pieces_for_player(self.next_player):
            for dest in get_piece_moves(piece, point, self.board):
                move = Move(point, dest)
                if self._is_move_legal(move):
                    moves.append(move)
        return moves

    def _is_move_legal(self, move):
        """走子后己方将不被吃、将帅不对面。"""
        next_state = self.apply_move(move)
        nb = next_state.board
        if nb.generals_facing():
            return False
        our_general = nb.find_general(self.next_player)
        if our_general is None:
            return False
        opponent = self.next_player.other
        for pt, pc in nb.pieces_for_player(opponent):
            if our_general in get_piece_moves(pc, pt, nb):
                return False
        return True

    def is_over(self):
        if self.board.find_general(Player.red) is None:
            return True
        if self.board.find_general(Player.black) is None:
            return True
        return len(self.legal_moves()) == 0

    def winner(self):
        if not self.is_over():
            return None
        if self.board.find_general(Player.red) is None:
            return Player.black
        if self.board.find_general(Player.black) is None:
            return Player.red
        return self.next_player.other  # 困毙：当前方无合法走法，对方胜
