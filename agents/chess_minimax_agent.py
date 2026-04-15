"""
Minimax 搜索象棋AI（无剪枝）。

算法：纯 Minimax 搜索 + 迭代加深 + 时间控制
用途：与 Alpha-Beta 对比，验证剪枝效果

注意：无剪枝时搜索深度受限，建议 max_depth=2-3
"""

import time

from cchess import GameState, Move, Player, PieceType
from cchess.ccboard import Board
from cchess.ccmoves import get_piece_moves
from cchess.evaluate import evaluate, EvalParams, DEFAULT_PARAMS, MATE_SCORE

__all__ = ["ChessMinimaxAgent"]

_CAPTURE_ORDER = {
    PieceType.GENERAL: 7, PieceType.CHARIOT: 6, PieceType.CANNON: 5,
    PieceType.HORSE: 4, PieceType.ADVISOR: 3, PieceType.ELEPHANT: 2,
    PieceType.PAWN: 1,
}

MAX_DEPTH = 4  # 无剪枝时深度受限


class ChessMinimaxAgent:
    """纯 Minimax 搜索 AI，无 Alpha-Beta 剪枝"""

    def __init__(self, time_limit=5.0, max_depth=3,
                 eval_fn=None, eval_params=None, verbose=True):
        """
        Args:
            time_limit: 每步思考时间（秒）
            max_depth: 最大搜索深度（建议2-3，无剪枝时较慢）
            eval_fn: 评估函数
            eval_params: 评估参数
            verbose: 是否输出调试信息
        """
        self.time_limit = time_limit
        self.max_depth = max_depth
        self.eval_fn = eval_fn or evaluate
        self.eval_params = eval_params or DEFAULT_PARAMS
        self.verbose = verbose
        self._start_time = 0.0
        self._nodes = 0

    def select_move(self, game_state: GameState) -> Move:
        """Minimax 搜索主入口"""
        self._start_time = time.time()
        self._nodes = 0

        best_move = None
        reached_depth = 0
        moves = game_state.legal_moves()
        if len(moves) == 1:
            return moves[0]

        # 迭代加深
        for depth in range(1, self.max_depth + 1):
            if self._time_up(0.8):
                break
            move, score = self._root_search(game_state, depth)
            reached_depth = depth
            if move is not None:
                best_move = move
            if abs(score) >= MATE_SCORE - self.max_depth:
                break

        elapsed = time.time() - self._start_time
        if self.verbose:
            print(f"[MM] depth={reached_depth}, nodes={self._nodes}, "
                  f"time={elapsed:.2f}s, move={best_move}")
        return best_move if best_move else moves[0]

    def _root_search(self, state, depth):
        """根节点搜索（返回最佳走法和分数）"""
        board = state.board
        player = state.next_player
        best_move = None
        best_score = -MATE_SCORE * 2

        for move in self._sort_moves(state.legal_moves(), board):
            if self._time_up(0.9):
                break
            captured = board.make_move(move)
            # 纯 Minimax：不需要 alpha/beta 窗口
            score = -self._minimax(board, player.other, depth - 1)
            board.unmake_move(move, captured)
            if score > best_score:
                best_score = score
                best_move = move

        return best_move, best_score

    def _minimax(self, board, player, depth):
        """
        纯 Minimax 搜索（无剪枝）

        返回：当前局面的评估分数
        """
        self._nodes += 1

        # 终局检测：将被吃
        if board.find_general(player) is None:
            return -(MATE_SCORE - (self.max_depth - depth))
        if board.find_general(player.other) is None:
            return MATE_SCORE - (self.max_depth - depth)

        # 叶节点：达到深度限制或时间用完
        if depth == 0 or self._time_up(0.95):
            return self.eval_fn(board, player, self.eval_params)

        # 生成合法走法
        moves = self._gen_legal_moves(board, player)
        if not moves:
            return -(MATE_SCORE - (self.max_depth - depth))  # 困毙

        # 走法排序（仍然有用，即使不剪枝）
        moves = self._sort_moves(moves, board)

        # Minimax：遍历所有子节点，取最大值
        best_score = -MATE_SCORE * 2
        for move in moves:
            captured = board.make_move(move)
            score = -self._minimax(board, player.other, depth - 1)
            board.unmake_move(move, captured)
            if score > best_score:
                best_score = score

        return best_score

    def _gen_legal_moves(self, board, player):
        """生成合法走法（make/unmake 检测将军）"""
        moves = []
        for pt, pc in board.pieces_for_player(player):
            for dest in get_piece_moves(pc, pt, board):
                move = Move(pt, dest)
                captured = board.make_move(move)
                legal = True
                if board.generals_facing():
                    legal = False
                elif board.find_general(player) is None:
                    legal = False
                else:
                    gen_pos = board.find_general(player)
                    for opt, opc in board.pieces_for_player(player.other):
                        if gen_pos in get_piece_moves(opc, opt, board):
                            legal = False
                            break
                board.unmake_move(move, captured)
                if legal:
                    moves.append(move)
        return moves

    def _sort_moves(self, moves, board):
        """走法排序（MVV-LVA，仍然有助于搜索效率）"""
        scored = []
        for move in moves:
            captured = board.get(move.to_point)
            if captured is not None:
                mover = board.get(move.from_point)
                mvv = _CAPTURE_ORDER.get(captured.piece_type, 0)
                lva = _CAPTURE_ORDER.get(mover.piece_type, 0)
                score = 10000 + mvv * 10 - lva
            else:
                score = 0
            scored.append((score, move))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]

    def _time_up(self, ratio=1.0):
        """检查时间是否用完"""
        return (time.time() - self._start_time) >= self.time_limit * ratio
