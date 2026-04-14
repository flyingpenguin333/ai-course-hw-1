"""随机走子象棋AI，用于验证规则框架。"""

import random
from cchess import GameState, Move


class ChessRandomAgent:
    def select_move(self, game_state: GameState) -> Move:
        legal = game_state.legal_moves()
        return random.choice(legal)
