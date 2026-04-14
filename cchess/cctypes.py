"""
中国象棋基础类型定义模块。

提供 Player（玩家）枚举、Point（坐标点）、PieceType（棋子类型）枚举
和 Piece（棋子）类型，作为整个象棋引擎的基础构建块。
"""

import enum
from collections import namedtuple

__all__ = ["Player", "Point", "PieceType", "Piece"]


class Player(enum.Enum):
    """玩家枚举。红方先行。"""
    red = 1
    black = 2

    @property
    def other(self):
        return Player.red if self == Player.black else Player.black


class PieceType(enum.Enum):
    """棋子类型枚举。"""
    GENERAL = 'general'    # 将/帅
    ADVISOR = 'advisor'    # 士/仕
    ELEPHANT = 'elephant'  # 象/相
    HORSE = 'horse'        # 马/馬
    CHARIOT = 'chariot'    # 车/車
    CANNON = 'cannon'      # 炮/砲
    PAWN = 'pawn'          # 兵/卒


class Point(namedtuple("Point", "row col")):
    """
    棋盘坐标点。0-indexed: row 0-9, col 0-8。
    row 0 = 红方底线, row 9 = 黑方底线。
    """
    def __deepcopy__(self, memodict=None):
        return self


class Piece(namedtuple("Piece", "player piece_type")):
    """棋子：(玩家, 棋子类型)。不可变，可哈希。"""
    def __deepcopy__(self, memodict=None):
        return self
