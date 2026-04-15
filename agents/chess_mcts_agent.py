"""
MCTS (蒙特卡洛树搜索) 象棋AI。

算法：四个步骤 - 选择、扩展、模拟、反向传播
优化：UCB1公式、时间控制
评估：末端局面用简单评估函数或随机模拟
"""

import random
import time
import math
from dataclasses import dataclass, field
from typing import Optional, Dict, List

from cchess import GameState, Move, Player
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
    total_reward: float = 0.0

    # 子节点
    children: Dict[Move, 'MCTSNode'] = field(default_factory=dict)

    @property
    def reward(self) -> float:
        """平均奖励"""
        if self.visits == 0:
            return 0.0
        return self.total_reward / self.visits

    def is_fully_expanded(self) -> bool:
        """是否所有子节点都已扩展"""
        legal_moves = self.state.legal_moves()
        return len(self.children) == len(legal_moves)

    def get_unexplored_move(self) -> Optional[Move]:
        """获取未扩展的走法"""
        legal_moves = self.state.legal_moves()
        for move in legal_moves:
            if move not in self.children:
                return move
        return None


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
        模拟对局至终局

        返回: 从当前玩家视角的奖励 (胜=1, 负=-1, 平=0)
        """
        # 如果游戏已结束，直接返回结果
        if state.is_over():
            winner = state.winner()
            current_player = state.next_player

            if winner is None:  # 平局
                return 0.0
            elif winner == current_player:
                return 1.0
            else:
                return -1.0

        # 快速模拟：随机走子直到终局或达到深度限制
        sim_state = state
        max_depth = 50  # 防止无限循环

        for _ in range(max_depth):
            if sim_state.is_over():
                break

            # 随机选择一个合法走法
            moves = sim_state.legal_moves()
            if not moves:
                break

            # 简单启发式：优先选择吃子走法
            capture_moves = [m for m in moves
                           if sim_state.board.get(m.to_point) is not None]

            if capture_moves and random.random() < 0.7:
                move = random.choice(capture_moves)
            else:
                move = random.choice(moves)

            sim_state = sim_state.apply_move(move)

        # 评估最终局面
        if sim_state.is_over():
            winner = sim_state.winner()
            original_player = state.next_player

            if winner is None:
                return 0.0
            elif winner == original_player:
                return 1.0
            else:
                return -1.0
        else:
            # 未到终局，用评估函数评估
            score = self.eval_fn(sim_state.board, state.next_player, self.eval_params)
            # 将评估值归一化到 [-1, 1]
            return math.tanh(score / 1000.0)

    def _backpropagate(self, node: MCTSNode, reward: float):
        """反向传播更新路径上所有节点的统计信息"""
        while node is not None:
            node.visits += 1
            # 注意：从对手视角看，奖励需要取反
            node.total_reward += reward
            reward = -reward  # 换边
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
