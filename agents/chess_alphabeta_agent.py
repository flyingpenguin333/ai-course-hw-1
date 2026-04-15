"""
Alpha-Beta 搜索象棋AI。

算法：Negamax + Alpha-Beta 剪枝 + 迭代加深 + 时间控制
优化：make/unmake（零拷贝）+ 走法排序（MVV-LVA + 历史启发）+ 置换表
评估：可插拔 eval_fn 接口，便于附加题替换评估函数
"""

import time

from cchess import GameState, Move, Player, PieceType
from cchess.ccboard import Board
from cchess.ccmoves import get_piece_moves
from cchess.evaluate import evaluate, EvalParams, DEFAULT_PARAMS, MATE_SCORE

__all__ = ["ChessAlphaBetaAgent"]

_EXACT, _LOWER, _UPPER = 0, 1, 2

_CAPTURE_ORDER = {
    PieceType.GENERAL: 7, PieceType.CHARIOT: 6, PieceType.CANNON: 5,
    PieceType.HORSE: 4, PieceType.ADVISOR: 3, PieceType.ELEPHANT: 2,
    PieceType.PAWN: 1,
}

MAX_DEPTH = 20


class ChessAlphaBetaAgent:
    def __init__(self, time_limit=5.0, max_depth=MAX_DEPTH,
                 eval_fn=None, eval_params=None, verbose=True):
        self.time_limit = time_limit
        self.max_depth = max_depth
        self.eval_fn = eval_fn or evaluate
        self.eval_params = eval_params or DEFAULT_PARAMS
        self.verbose = verbose
        self._tt = {}
        self._history = {}
        self._start_time = 0.0
        self._nodes = 0

    def select_move(self, game_state: GameState) -> Move:
        self._start_time = time.time()
        self._nodes = 0
        self._reached_depth = 0
        self._tt.clear()
        self._history.clear()

        best_move = None
        moves = game_state.legal_moves()
        if len(moves) == 1:
            return moves[0]

        for depth in range(1, self.max_depth + 1):
            if self._time_up(0.8):
                break
            move, score = self._root_search(game_state, depth)
            self._reached_depth = depth
            if move is not None:
                best_move = move
            if abs(score) >= MATE_SCORE - self.max_depth:
                break

        elapsed = time.time() - self._start_time
        if self.verbose:
            print(f"[AB] depth={self._reached_depth}, nodes={self._nodes}, "
                  f"time={elapsed:.2f}s, move={best_move}")
        return best_move if best_move else moves[0]

    def _root_search(self, state, depth):
        board = state.board
        player = state.next_player
        alpha = -MATE_SCORE * 2
        beta = MATE_SCORE * 2
        best_move = None
        best_score = alpha

        for move in self._sort_moves(state.legal_moves(), board):
            if self._time_up(0.9):
                break
            captured = board.make_move(move)
            score = -self._negamax(board, player.other, depth - 1, -beta, -alpha)
            board.unmake_move(move, captured)
            if score > best_score:
                best_score = score
                best_move = move
                alpha = max(alpha, score)
        return best_move, best_score

    def _negamax(self, board, player, depth, alpha, beta):
        self._nodes += 1

        # 置换表
        key = self._board_hash(board, player)
        tt = self._tt.get(key)
        if tt is not None:
            td, ts, tf, tm = tt
            if td >= depth:
                if tf == _EXACT:
                    return ts
                elif tf == _LOWER:
                    alpha = max(alpha, ts)
                elif tf == _UPPER:
                    beta = min(beta, ts)
                if alpha >= beta:
                    return ts

        # 终局检测：将被吃
        if board.find_general(player) is None:
            return -(MATE_SCORE - (self.max_depth - depth))
        if board.find_general(player.other) is None:
            return MATE_SCORE - (self.max_depth - depth)

        # 叶节点
        if depth == 0 or self._time_up(0.95):
            return self.eval_fn(board, player, self.eval_params)

        # 生成合法走法
        moves = self._gen_legal_moves(board, player)
        if not moves:
            return -(MATE_SCORE - (self.max_depth - depth))  # 困毙

        # 走法排序
        moves = self._sort_moves(moves, board)

        orig_alpha = alpha
        best_score = -MATE_SCORE * 2
        best_move = None

        for move in moves:
            captured = board.make_move(move)
            score = -self._negamax(board, player.other, depth - 1, -beta, -alpha)
            board.unmake_move(move, captured)

            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, score)
            if alpha >= beta:
                hk = (move.from_point, move.to_point)
                self._history[hk] = self._history.get(hk, 0) + depth * depth
                break

        # 存置换表
        if best_score <= orig_alpha:
            flag = _UPPER
        elif best_score >= beta:
            flag = _LOWER
        else:
            flag = _EXACT
        self._tt[key] = (depth, best_score, flag, best_move)
        return best_score

    def _gen_legal_moves(self, board, player):
        """生成合法走法（make/unmake 检测将军）。"""
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
        scored = []
        for move in moves:
            captured = board.get(move.to_point)
            if captured is not None:
                mover = board.get(move.from_point)
                mvv = _CAPTURE_ORDER.get(captured.piece_type, 0)
                lva = _CAPTURE_ORDER.get(mover.piece_type, 0)
                score = 10000 + mvv * 10 - lva
            else:
                score = self._history.get((move.from_point, move.to_point), 0)
            scored.append((score, move))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]

    def _board_hash(self, board, player):
        return hash((frozenset(board._grid.items()), player))

    def _time_up(self, ratio=1.0):
        return (time.time() - self._start_time) >= self.time_limit * ratio
