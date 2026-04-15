"""
中国象棋评估函数模块 (EVAL7 风格，参考 PDF04)。

提供参数化的评估函数接口：evaluate(board, player, params) -> float
正值表示对 player 有利。

特征体系 (EVAL7 = MATL + LOC + MOB + AKA + SPC + COP):
  MATL: 子力价值 (7个权重)
  LOC:  位置价值表 (194特征，硬编码)
  MOB:  每种棋子的安全机动性 (7个权重)
  AKA:  攻击将帅相邻格子 (5个权重，按攻击子类型)
  SPC:  安全潜在将军 (5个权重，按将军子类型)
  COP:  追逐对方棋子 (1个权重)

三个版本递进：
  evaluate    — v1: MATL + LOC
  evaluate_v2 — v2: v1 + MOB (按棋子类型分别计权)
  evaluate_v3 — v3: v2 + AKA + SPC + COP
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
    """评估函数可调参数 - PDF04 EVAL7 风格，共25个权重。"""
    # MATL: 子力价值 (7个)
    w_chariot: int = 900
    w_cannon: int = 450
    w_horse: int = 400
    w_advisor: int = 200
    w_elephant: int = 200
    w_pawn: int = 100
    w_pawn_crossed: int = 100   # 过河兵额外加成

    # MOB: 机动性 (7个权重，每种棋子类型一个)
    w_mob_chariot: float = 0.0
    w_mob_cannon: float = 0.0
    w_mob_horse: float = 0.0
    w_mob_advisor: float = 0.0
    w_mob_elephant: float = 0.0
    w_mob_pawn: float = 0.0
    w_mob_general: float = 0.0   # 将/帅的机动性通常不重要

    # AKA: 攻击将帅相邻格子 (5个权重)
    w_aka_chariot: float = 0.0
    w_aka_knight: float = 0.0
    w_aka_cannon: float = 0.0
    w_aka_advisor: float = 0.0
    w_aka_elephant: float = 0.0

    # SPC: 安全潜在将军 (5个权重)
    w_spc_chariot: float = 0.0
    w_spc_knight: float = 0.0
    w_spc_cannon: float = 0.0
    w_spc_advisor: float = 0.0
    w_spc_elephant: float = 0.0

    # COP: 追逐对方棋子 (1个权重)
    w_chase: float = 0.0

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
    [ 0,  0,  0,  2, 6, 2,  0,  0,  0],
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
    [ 0,  0,  0,  0,  0,  0,  0, 0,  0],
    [ 0,  0,   0, 0,  0,  0,  0,  0,  0],
    [ 0, 0,  0, 0, 0, 0, 0, 0, 0, 0],
    [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [ 0,  0, 0, 0, 0, 0, 0, 0, 0, 0],
]

_ADVISOR_TABLE = [
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0, 20,  0, 20,  0,  0,  0],
    [ 0,  0,  0,  0, 23,  0,  0,  0,  0],
    [ 0,  0,  0, 20,  0, 20,  0, 0,  0],
    [ 0,  0,  0,  0,  0, 0, 0, 0, 0, 0],
    [ 0,  0,  0, 0, 0, 0, 0, 0, 0, 0],
    [ 0,  0, 0, 0, 0, 0, 0, 0, 0, 0],
    [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [ 0,  0, 0, 0, 0, 0, 0, 0, 0, 0],
]

_ELEPHANT_TABLE = [
    [ 0,  0, 20,  0,  0,  0, 20,  0,  0],
    [ 0,  0,  0,   0, 0,  0, 0,  0, 0],
    [18,  0, 0,  0, 23,  0, 0, 0, 18],
    [ 0,  0, 0, 0, 0,  0, 0, 0,  0],
    [ 0, 0, 20, 0, 0, 0, 20, 0, 0, 0],
    [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [ 0,  0, 0, 0, 0, 0, 0, 0, 0, 0],
    [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
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


def _piece_value(piece_type, params):
    return {
        PieceType.GENERAL:  MATE_SCORE,
        PieceType.CHARIOT:  params.w_chariot,
        PieceType.CANNON:   params.w_cannon,
        PieceType.HORSE:    params.w_horse,
        PieceType.ADVISOR:  params.w_advisor,
        PieceType.ELEPHANT: params.w_elephant,
        PieceType.PAWN:     params.w_pawn,
    }[piece_type]


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
    """v1: MATL + LOC (子力 + 位置价值表)。"""
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


# ── 特征计算函数 (EVAL7) ────────────────────────────────


def _is_safe_square(square, player, board):
    """检查格子是否安全（不被对方攻击）。"""
    opponent = player.other
    for pt, pc in board._grid.items():
        if pc.player == opponent and square in get_piece_moves(pc, pt, board):
            return False
    return True


def _get_adjacent_squares(gen_pos, player):
    """获取将帅九宫内相邻格。"""
    adj_squares = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        sq = Point(gen_pos.row + dr, gen_pos.col + dc)
        if in_palace(sq, player):
            adj_squares.append(sq)
    return adj_squares


def _mobility_score(board, player, params):
    """MOB: 每种棋子的安全机动性，使用对应权重。"""
    mobility = {pt: 0 for pt in PieceType}
    for pt, pc in board._grid.items():
        if pc.player != player:
            continue
        moves = get_piece_moves(pc, pt, board)
        safe_moves = sum(1 for dest in moves if _is_safe_square(dest, player, board))
        mobility[pc.piece_type] += safe_moves
    score = (mobility[PieceType.CHARIOT] * params.w_mob_chariot +
             mobility[PieceType.CANNON] * params.w_mob_cannon +
             mobility[PieceType.HORSE] * params.w_mob_horse +
             mobility[PieceType.ADVISOR] * params.w_mob_advisor +
             mobility[PieceType.ELEPHANT] * params.w_mob_elephant +
             mobility[PieceType.PAWN] * params.w_mob_pawn +
             mobility[PieceType.GENERAL] * params.w_mob_general)
    return score


def _aka_score(board, player, params):
    """AKA: 对方攻击己方将帅相邻格数（按攻击子类型计权）。"""
    gen_pos = board.find_general(player)
    if gen_pos is None:
        return -500
    opponent = player.other
    adj_squares = _get_adjacent_squares(gen_pos, player)
    attacks_by_type = {
        PieceType.CHARIOT: 0, PieceType.HORSE: 0, PieceType.CANNON: 0,
        PieceType.ADVISOR: 0, PieceType.ELEPHANT: 0,
    }
    for sq in adj_squares:
        for pt, pc in board._grid.items():
            if pc.player != opponent or pc.piece_type not in attacks_by_type:
                continue
            if sq in get_piece_moves(pc, pt, board):
                attacks_by_type[pc.piece_type] += 1
                break
    score = -(attacks_by_type[PieceType.CHARIOT] * params.w_aka_chariot +
             attacks_by_type[PieceType.HORSE] * params.w_aka_knight +
             attacks_by_type[PieceType.CANNON] * params.w_aka_cannon +
             attacks_by_type[PieceType.ADVISOR] * params.w_aka_advisor +
             attacks_by_type[PieceType.ELEPHANT] * params.w_aka_elephant)
    return score


def _spc_score(board, player, params):
    """SPC: 己方安全潜在将军数（按将军子类型计权）。"""
    opponent = player.other
    opp_gen_pos = board.find_general(opponent)
    if opp_gen_pos is None:
        return 500
    safe_checks_by_type = {
        PieceType.CHARIOT: 0, PieceType.HORSE: 0, PieceType.CANNON: 0,
        PieceType.ADVISOR: 0, PieceType.ELEPHANT: 0,
    }
    for pt, pc in board._grid.items():
        if pc.player != player or pc.piece_type not in safe_checks_by_type:
            continue
        for dest in get_piece_moves(pc, pt, board):
            captured = board.make_move(Move(pt, dest))
            checking = opp_gen_pos in get_piece_moves(pc, dest, board)
            safe = True
            if checking:
                for opt, opc in board._grid.items():
                    if opc.player == opponent and dest in get_piece_moves(opc, opt, board):
                        safe = False
                        break
            board.unmake_move(Move(pt, dest), captured)
            if checking and safe:
                safe_checks_by_type[pc.piece_type] += 1
    score = (safe_checks_by_type[PieceType.CHARIOT] * params.w_spc_chariot +
             safe_checks_by_type[PieceType.HORSE] * params.w_spc_knight +
             safe_checks_by_type[PieceType.CANNON] * params.w_spc_cannon +
             safe_checks_by_type[PieceType.ADVISOR] * params.w_spc_advisor +
             safe_checks_by_type[PieceType.ELEPHANT] * params.w_spc_elephant)
    return score


def _cop_score(board, player, params):
    """COP: 追逐对方棋子（简化版：统计被攻击的对方棋子数差）。"""
    opponent = player.other
    my_chases = 0
    for pt, pc in board._grid.items():
        if pc.player != player:
            continue
        moves = get_piece_moves(pc, pt, board)
        for dest in moves:
            target = board.get(dest)
            if target and target.player == opponent:
                my_chases += 1
                break
    opp_chases = 0
    for pt, pc in board._grid.items():
        if pc.player != opponent:
            continue
        moves = get_piece_moves(pc, pt, board)
        for dest in moves:
            target = board.get(dest)
            if target and target.player == player:
                opp_chases += 1
                break
    return (my_chases - opp_chases) * params.w_chase


# ── v2/v3 评估函数 ────────────────────────────────────────


def evaluate_v2(board, player, params=None):
    """v2: MATL + LOC + MOB (按棋子类型分别计权)。"""
    if params is None:
        params = DEFAULT_PARAMS
    score = evaluate(board, player, params)
    score += _mobility_score(board, player, params)
    return score


def evaluate_v3(board, player, params=None):
    """v3: v2 + AKA + SPC + COP。"""
    if params is None:
        params = DEFAULT_PARAMS
    score = evaluate_v2(board, player, params)
    score += _aka_score(board, player, params)
    score += _spc_score(board, player, params)
    score += _cop_score(board, player, params)
    return score
