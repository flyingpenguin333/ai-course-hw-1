"""
MCTS (蒙特卡洛树搜索) 象棋AI。

算法：四个步骤 - 选择、扩展、模拟、反向传播
优化：UCB1公式、时间控制
评估：快速蒙特卡洛模拟（材料评估）
"""

import random
import time
import math
from dataclasses import dataclass, field
from typing import Optional, Dict, List

from cchess import GameState, Move, Player, PieceType
from cchess.evaluate import evaluate, EvalParams, DEFAULT_PARAMS

__all__ = ["ChessMCTSAgent"]


@dataclass
class MCTSNode:
    """MCTS树节点"""
    state: GameState
    parent: Optional['MCTSNode'] = None
    move: Optional[Move] = None  # 从父节点到此节点的走法

    # 统计信息
    visits: int = 0
    total_reward: float = 0.0  # 从父节点视角累计奖励

    # 子节点
    children: Dict[Move, 'MCTSNode'] = field(default_factory=dict)
    _untried_moves: Optional[List] = field(default=None, repr=False)

    def _init_untried(self):
        if self._untried_moves is None:
            self._untried_moves = list(self.state.legal_moves())

    @property
    def reward(self) -> float:
        """平均奖励（父节点视角）"""
        if self.visits == 0:
            return 0.0
        return self.total_reward / self.visits

    def is_fully_expanded(self) -> bool:
        self._init_untried()
        return len(self._untried_moves) == 0

    def get_unexplored_move(self) -> Optional[Move]:
        self._init_untried()
        if not self._untried_moves:
            return None
        # 随机选一个未尝试的走法并移除
        idx = random.randrange(len(self._untried_moves))
        move = self._untried_moves[idx]
        self._untried_moves[idx] = self._untried_moves[-1]
        self._untried_moves.pop()
        return move


class ChessMCTSAgent:
    """MCTS象棋AI"""

    def __init__(self, time_limit=5.0, exploration_constant=1.414,
                 eval_fn=None, eval_params=None, verbose=True):
        """
        Args:
            time_limit: 每步思考时间（秒）
            exploration_constant: UCB1探索常数C，默认√2
            eval_fn: 评估函数（用于末端局面）
            eval_params: 评估参数
            verbose: 是否输出调试信息
        """
        self.time_limit = time_limit
        self.C = exploration_constant
        self.eval_fn = eval_fn or evaluate
        self.eval_params = eval_params or DEFAULT_PARAMS
        self.verbose = verbose
        self._start_time = 0.0
        self._simulations = 0

    def select_move(self, game_state: GameState) -> Move:
        """MCTS主循环：选择最佳走法"""
        self._start_time = time.time()
        self._simulations = 0

        # 根节点
        root = MCTSNode(game_state)

        # 在时间限制内运行MCTS
        while not self._time_up():
            # 1. 选择
            node = self._select(root)

            # 2. 扩展
            if not node.state.is_over() and not node.is_fully_expanded():
                node = self._expand(node)

            # 3. 模拟
            reward = self._simulate(node.state)

            # 4. 反向传播
            self._backpropagate(node, reward)

            self._simulations += 1

        # 选择访问次数最多的子节点
        best_move = self._best_move(root)

        elapsed = time.time() - self._start_time
        if self.verbose:
            print(f"[MCTS] simulations={self._simulations}, "
                  f"time={elapsed:.2f}s, move={best_move}")

        return best_move

    def _select(self, node: MCTSNode) -> MCTSNode:
        """UCB1选择：从根节点选择一个叶子节点"""
        while node.is_fully_expanded() and not node.state.is_over():
            # 选择UCB1值最大的子节点
            node = max(node.children.values(), key=self._ucb1)
        return node

    def _expand(self, node: MCTSNode) -> MCTSNode:
        """扩展一个未探索的走法"""
        move = node.get_unexplored_move()
        if move is None:
            return node

        # 应用走法得到新状态
        new_state = node.state.apply_move(move)

        # 创建新节点
        child_node = MCTSNode(new_state, parent=node, move=move)
        node.children[move] = child_node

        return child_node

    def _simulate(self, state: GameState) -> float:
        """
        混合模拟：在 board 上直接 make/unmake（零拷贝），随机走 N 步后用 evaluate() 评估。
        返回: 从 state.next_player 视角的奖励。
        """
        from cchess.ccmoves import get_piece_moves
        from cchess import Player

        board = state.board
        original_player = state.next_player
        current_player = original_player

        # 如果游戏已结束
        if board.find_general(Player.red) is None:
            winner = Player.black
        elif board.find_general(Player.black) is None:
            winner = Player.red
        else:
            winner = None

        if winner is not None:
            return 1.0 if winner == original_player else -1.0

        # 记录走法历史，用于 unmake
        history = []
        max_depth = 5

        for _ in range(max_depth):
            # 快速生成走法（不检查将军）
            moves = []
            for pt, pc in board.pieces_for_player(current_player):
                for dest in get_piece_moves(pc, pt, board):
                    moves.append(Move(pt, dest))

            if not moves:
                break

            # 优先吃子
            capture_moves = [m for m in moves if board.get(m.to_point) is not None]
            move = random.choice(capture_moves if capture_moves and random.random() < 0.7 else moves)

            captured = board.make_move(move)
            history.append((move, captured))
            current_player = current_player.other

            # 检查将被吃（终局）：刚走子方可能吃掉了 current_player 的将
            if board.find_general(current_player) is None:
                break

        # 评估当前局面（从 original_player 视角）
        score = self.eval_fn(board, original_player, self.eval_params)

        # unmake 所有走法
        for move, captured in reversed(history):
            board.unmake_move(move, captured)

        return math.tanh(score / 1000.0)

    def _get_fast_moves(self, state):
        """快速生成走法（不检查将军等复杂规则）"""
        from cchess.ccmoves import get_piece_moves
        moves = []
        for point, piece in state.board.pieces_for_player(state.next_player):
            for dest in get_piece_moves(piece, point, state.board):
                moves.append(Move(point, dest))
        return moves

    def _count_material(self, state, player):
        """简单计算材料分"""
        piece_values = {
            PieceType.GENERAL: 10000,
            PieceType.CHARIOT: 900,
            PieceType.CANNON: 450,
            PieceType.HORSE: 400,
            PieceType.ADVISOR: 200,
            PieceType.ELEPHANT: 200,
            PieceType.PAWN: 100,
        }
        total = 0
        for _, piece in state.board.pieces_for_player(player):
            total += piece_values.get(piece.piece_type, 0)
        return total

    def _backpropagate(self, node: MCTSNode, reward: float):
        """
        反向传播。reward 是从 node.state.next_player 视角的奖励。
        node.total_reward 存父节点视角的奖励（UCB1 用于父节点选子节点）。
        """
        while node is not None:
            node.visits += 1
            reward = -reward             # 转换为父节点视角
            node.total_reward += reward  # 父节点视角
            node = node.parent

    def _ucb1(self, node: MCTSNode) -> float:
        """UCB1公式：平衡探索与利用"""
        if node.visits == 0:
            return float('inf')

        parent = node.parent
        if parent is None:
            return node.reward

        exploit = node.reward
        explore = self.C * math.sqrt(math.log(parent.visits) / node.visits)

        return exploit + explore

    def _best_move(self, node: MCTSNode) -> Move:
        """选择访问次数最多的走法"""
        if not node.children:
            # 没有子节点，返回随机合法走法
            moves = node.state.legal_moves()
            return random.choice(moves) if moves else None

        return max(node.children.items(), key=lambda x: x[1].visits)[0]

    def _time_up(self) -> bool:
        """检查时间是否用完"""
        return (time.time() - self._start_time) >= self.time_limit
