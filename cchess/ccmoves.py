"""
中国象棋各棋子走法生成模块。

每种棋子一个函数，返回伪合法目标位置列表（不含将军检测，由 GameState 过滤）。
"""

from .cctypes import Player, Point, PieceType

__all__ = ["get_piece_moves", "is_on_board", "in_palace", "on_own_side", "crossed_river"]

ROWS, COLS = 10, 9


def is_on_board(point):
    return 0 <= point.row < ROWS and 0 <= point.col < COLS


def in_palace(point, player):
    if player == Player.red:
        return 0 <= point.row <= 2 and 3 <= point.col <= 5
    return 7 <= point.row <= 9 and 3 <= point.col <= 5


def on_own_side(point, player):
    if player == Player.red:
        return point.row <= 4
    return point.row >= 5


def crossed_river(point, player):
    if player == Player.red:
        return point.row >= 5
    return point.row <= 4


def _not_own_piece(board, point, player):
    """目标位置没有己方棋子（空位或对方棋子均可）。"""
    piece = board.get(point)
    return piece is None or piece.player != player


# ── 将/帅 ──────────────────────────────────────────────
def general_moves(point, player, board):
    moves = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        dest = Point(point.row + dr, point.col + dc)
        if in_palace(dest, player) and _not_own_piece(board, dest, player):
            moves.append(dest)
    return moves


# ── 士/仕 ──────────────────────────────────────────────
def advisor_moves(point, player, board):
    moves = []
    for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        dest = Point(point.row + dr, point.col + dc)
        if in_palace(dest, player) and _not_own_piece(board, dest, player):
            moves.append(dest)
    return moves


# ── 象/相 ──────────────────────────────────────────────
def elephant_moves(point, player, board):
    moves = []
    for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        mid = Point(point.row + dr, point.col + dc)
        dest = Point(point.row + 2 * dr, point.col + 2 * dc)
        if (is_on_board(dest) and on_own_side(dest, player)
                and board.get(mid) is None
                and _not_own_piece(board, dest, player)):
            moves.append(dest)
    return moves


# ── 马/馬 ──────────────────────────────────────────────
def horse_moves(point, player, board):
    moves = []
    # 先正交1步（检查蹩马腿），再对角1步
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        blocking = Point(point.row + dr, point.col + dc)
        if not is_on_board(blocking) or board.get(blocking) is not None:
            continue  # 蹩马腿
        # 从正交方向延伸出两个对角目标
        if dr != 0:  # 纵向先走
            for dc2 in [-1, 1]:
                dest = Point(point.row + 2 * dr, point.col + dc2)
                if is_on_board(dest) and _not_own_piece(board, dest, player):
                    moves.append(dest)
        else:  # 横向先走
            for dr2 in [-1, 1]:
                dest = Point(point.row + dr2, point.col + 2 * dc)
                if is_on_board(dest) and _not_own_piece(board, dest, player):
                    moves.append(dest)
    return moves


# ── 车/車 ──────────────────────────────────────────────
def chariot_moves(point, player, board):
    moves = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        r, c = point.row + dr, point.col + dc
        while 0 <= r < ROWS and 0 <= c < COLS:
            dest = Point(r, c)
            piece = board.get(dest)
            if piece is None:
                moves.append(dest)
            else:
                if piece.player != player:
                    moves.append(dest)  # 吃子
                break
            r += dr
            c += dc
    return moves


# ── 炮/砲 ──────────────────────────────────────────────
def cannon_moves(point, player, board):
    moves = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        r, c = point.row + dr, point.col + dc
        # 阶段1：移动（不吃子），遇到第一个子停下
        while 0 <= r < ROWS and 0 <= c < COLS:
            dest = Point(r, c)
            if board.get(dest) is None:
                moves.append(dest)
            else:
                # 找到炮架，进入阶段2
                r += dr
                c += dc
                while 0 <= r < ROWS and 0 <= c < COLS:
                    dest2 = Point(r, c)
                    piece2 = board.get(dest2)
                    if piece2 is not None:
                        if piece2.player != player:
                            moves.append(dest2)  # 隔子吃
                        break
                    r += dr
                    c += dc
                break
            r += dr
            c += dc
    return moves


# ── 兵/卒 ──────────────────────────────────────────────
def pawn_moves(point, player, board):
    moves = []
    forward = 1 if player == Player.red else -1
    # 前进
    dest = Point(point.row + forward, point.col)
    if is_on_board(dest) and _not_own_piece(board, dest, player):
        moves.append(dest)
    # 过河后可左右
    if crossed_river(point, player):
        for dc in [-1, 1]:
            dest = Point(point.row, point.col + dc)
            if is_on_board(dest) and _not_own_piece(board, dest, player):
                moves.append(dest)
    return moves


# ── 分发 ───────────────────────────────────────────────
_DISPATCH = {
    PieceType.GENERAL:  general_moves,
    PieceType.ADVISOR:  advisor_moves,
    PieceType.ELEPHANT: elephant_moves,
    PieceType.HORSE:    horse_moves,
    PieceType.CHARIOT:  chariot_moves,
    PieceType.CANNON:   cannon_moves,
    PieceType.PAWN:     pawn_moves,
}


def get_piece_moves(piece, point, board):
    return _DISPATCH[piece.piece_type](point, piece.player, board)
