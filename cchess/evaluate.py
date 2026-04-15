"""
中国象棋评估函数模块。

提供参数化的评估函数接口：evaluate(board, player, params) -> float
正值表示对 player 有利。

所有权重抽取为 EvalParams dataclass，便于自动调参（遗传算法/PSO）。

三个版本递进：
  evaluate    — v1: 子力 + 位置价值表
  evaluate_v2 — v2: v1 + 机动性
  evaluate_v3 — v3: v2 + 王安全
"""

import json
from dataclasses import dataclass, field, asdict, fields
from .cctypes import Player, Point, PieceType
from .ccmoves import get_piece_moves, in_palace

__all__ = ["evaluate", "evaluate_v2", "evaluate_v3",
           "EvalParams", "DEFAULT_PARAMS", "MATE_SCORE"]

MATE_SCORE = 100_000


@dataclass
class EvalParams:
    """评估函数可调参数。所有子力权重和特征权重集中于此。"""
    # 子力价值
    w_chariot: int = 900
    w_cannon: int = 450
    w_horse: int = 400
    w_advisor: int = 200
    w_elephant: int = 200
    w_pawn: int = 100
    w_pawn_crossed: int = 100   # 过河兵额外加成
    # 高级特征权重
    w_mobility: float = 0.0     # 机动性
    w_king_safety: float = 0.0  # 王安全

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        valid = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})

    def save(self, path):
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path):
        with open(path) as f:
            return cls.from_dict(json.load(f))


DEFAULT_PARAMS = EvalParams()


def _piece_value(piece_type, params):
    """从 params 获取棋子子力价值。"""
    return {
        PieceType.GENERAL:  MATE_SCORE,
        PieceType.CHARIOT:  params.w_chariot,
        PieceType.CANNON:   params.w_cannon,
        PieceType.HORSE:    params.w_horse,
        PieceType.ADVISOR:  params.w_advisor,
        PieceType.ELEPHANT: params.w_elephant,
        PieceType.PAWN:     params.w_pawn,
    }[piece_type]


# ── 位置价值表（红方视角，row 0=底线）──────────────────
# 黑方使用对称翻转：table[9-row][8-col]

_CHARIOT_TABLE = [
    [14, 14, 12, 18, 16, 18, 12, 14, 14],
    [16, 20, 18, 24, 26, 24, 18, 20, 16],
    [12, 12, 12, 18, 15, 18, 12, 12, 12],
    [12, 18, 16, 22, 22, 22, 16, 18, 12],
    [12, 14, 12, 18, 18, 18, 12, 14, 12],
    [12, 16, 14, 20, 20, 20, 14, 16, 12],
    [14, 14, 14, 20, 20, 20, 14, 14, 14],
    [16, 20, 18, 24, 24, 24, 18, 20, 16],
    [20, 24, 22, 30, 32, 30, 22, 24, 20],
    [20, 20, 20, 26, 28, 26, 20, 20, 20],
]

_HORSE_TABLE = [
    [ 4,  8, 16, 12,  4, 12, 16,  8,  4],
    [ 4, 10, 28, 16,  8, 16, 28, 10,  4],
    [ 8, 24, 18, 24, 20, 24, 18, 24,  8],
    [12, 16, 28, 34, 26, 34, 28, 16, 12],
    [ 8, 18, 16, 22, 22, 22, 16, 18,  8],
    [10, 14, 18, 22, 18, 22, 18, 14, 10],
    [ 4, 10, 14, 18, 16, 18, 14, 10,  4],
    [ 6,  8, 10, 14, 12, 14, 10,  8,  6],
    [ 4,  6,  8, 10,  8, 10,  8,  6,  4],
    [ 2,  4,  6,  6,  6,  6,  6,  4,  2],
]

_CANNON_TABLE = [
    [ 6,  4,  0,-10,-12,-10,  0,  4,  6],
    [ 2,  2,  0, -4,-14, -4,  0,  2,  2],
    [ 2,  6,  4,  0,-10,  0,  4,  6,  2],
    [ 0,  0,  0,  2,  8,  2,  0,  0,  0],
    [ 0,  0,  0,  2,  8,  2,  0,  0,  0],
    [-2,  0,  4,  2,  6,  2,  4,  0, -2],
    [ 0,  0,  0,  2,  6,  2,  0,  0,  0],
    [ 4,  0,  8,  6, 10,  6,  8,  0,  4],
    [ 0,  2,  4,  6,  6,  6,  4,  2,  0],
    [ 0,  0,  2,  6,  6,  6,  2,  0,  0],
]

_PAWN_TABLE = [
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 2,  0,  8,  0, 14,  0,  8,  0,  2],
    [ 2,  0,  8,  0, 14,  0,  8,  0,  2],
    [14, 18, 20, 27, 29, 27, 20, 18, 14],
    [20, 23, 23, 29, 30, 29, 23, 23, 20],
    [22, 24, 26, 32, 32, 32, 26, 24, 22],
    [22, 24, 26, 32, 32, 32, 26, 24, 22],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
]

_GENERAL_TABLE = [
    [ 0,  0,  0, -9,  0, -9,  0,  0,  0],
    [ 0,  0,  0, -9,  0, -9,  0,  0,  0],
    [ 0,  0,  0,  0,  9,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
]

_ADVISOR_TABLE = [
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0, 20,  0, 20,  0,  0,  0],
    [ 0,  0,  0,  0, 23,  0,  0,  0,  0],
    [ 0,  0,  0, 20,  0, 20,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
]

_ELEPHANT_TABLE = [
    [ 0,  0, 20,  0,  0,  0, 20,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [18,  0,  0,  0, 23,  0,  0,  0, 18],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0, 20,  0,  0,  0, 20,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
]

_POS_TABLES = {
    PieceType.GENERAL:  _GENERAL_TABLE,
    PieceType.ADVISOR:  _ADVISOR_TABLE,
    PieceType.ELEPHANT: _ELEPHANT_TABLE,
    PieceType.HORSE:    _HORSE_TABLE,
    PieceType.CHARIOT:  _CHARIOT_TABLE,
    PieceType.CANNON:   _CANNON_TABLE,
    PieceType.PAWN:     _PAWN_TABLE,
}


# ── 评估函数 ──────────────────────────────────────────

def _piece_score(piece, point, params):
    """单个棋子的子力 + 位置价值。"""
    base = _piece_value(piece.piece_type, params)
    if piece.piece_type == PieceType.PAWN:
        if piece.player == Player.red and point.row >= 5:
            base += params.w_pawn_crossed
        elif piece.player == Player.black and point.row <= 4:
            base += params.w_pawn_crossed
    table = _POS_TABLES[piece.piece_type]
    if piece.player == Player.red:
        pos_val = table[point.row][point.col]
    else:
        pos_val = table[9 - point.row][8 - point.col]
    return base + pos_val


def evaluate(board, player, params=None):
    """v1: 子力 + 位置价值表。"""
    if params is None:
        params = DEFAULT_PARAMS
    score = 0
    for pt, pc in board._grid.items():
        val = _piece_score(pc, pt, params)
        if pc.player == player:
            score += val
        else:
            score -= val
    return score


# ── PLACEHOLDER_V2V3 ──


def _mobility_score(board, player):
    """机动性：己方合法走法数 - 对方合法走法数。"""
    own = sum(len(get_piece_moves(pc, pt, board))
              for pt, pc in board._grid.items() if pc.player == player)
    opp = sum(len(get_piece_moves(pc, pt, board))
              for pt, pc in board._grid.items() if pc.player != player)
    return own - opp


def _king_safety_score(board, player):
    """
    王安全评估（参考PDF04的AKA特征）：
    - 士象完整度：每个士+15，每个象+15
    - 将周围被对方攻击的格数：每格-20
    """
    score = 0
    opponent = player.other
    # 士象完整度
    for pt, pc in board._grid.items():
        if pc.player == player:
            if pc.piece_type == PieceType.ADVISOR:
                score += 15
            elif pc.piece_type == PieceType.ELEPHANT:
                score += 15
    # 将周围被攻击格数
    gen_pos = board.find_general(player)
    if gen_pos is None:
        return -500
    adj_squares = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        sq = Point(gen_pos.row + dr, gen_pos.col + dc)
        if in_palace(sq, player):
            adj_squares.append(sq)
    # 检查对方棋子能否攻击这些格
    opp_pieces = [(pt, pc) for pt, pc in board._grid.items() if pc.player == opponent]
    attacked = 0
    for sq in adj_squares:
        for pt, pc in opp_pieces:
            if sq in get_piece_moves(pc, pt, board):
                attacked += 1
                break
    score -= attacked * 20
    return score


def evaluate_v2(board, player, params=None):
    """v2: v1 + 机动性。"""
    if params is None:
        params = DEFAULT_PARAMS
    score = evaluate(board, player, params)
    if params.w_mobility != 0:
        score += params.w_mobility * _mobility_score(board, player)
    return score


def evaluate_v3(board, player, params=None):
    """v3: v2 + 王安全。"""
    if params is None:
        params = DEFAULT_PARAMS
    score = evaluate_v2(board, player, params)
    if params.w_king_safety != 0:
        score += params.w_king_safety * _king_safety_score(board, player)
    return score
