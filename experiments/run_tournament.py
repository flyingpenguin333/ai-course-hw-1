"""
搜索算法对比实验：循环赛脚本

支持 4 种 Agents：
- Random: 随机走子
- Minimax: 纯 Minimax 无剪枝
- Alpha-Beta: Negamax + Alpha-Beta 剪枝
- MCTS: 蒙特卡洛树搜索

赛制：循环赛，每对指定局数，交换先后手
输出：详细统计（胜率、时间、节点数等）
"""

import argparse
import csv
import json
import os
import random
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cchess import GameState, Player
from agents.chess_random_agent import ChessRandomAgent
from agents.chess_minimax_agent import ChessMinimaxAgent
from agents.chess_alphabeta_agent import ChessAlphaBetaAgent
from agents.chess_mcts_agent import ChessMCTSAgent


@dataclass
class GameStats:
    """单局统计信息"""
    agent1_name: str
    agent2_name: str
    agent1_color: str  # 'red' or 'black'
    winner: str  # 'agent1', 'agent2', or 'draw'
    num_moves: int
    move_count_1: int   # agent1 实际走的步数
    move_count_2: int   # agent2 实际走的步数
    total_time_1: float
    total_time_2: float
    total_nodes_1: int  # 对于 MCTS 是模拟次数
    total_nodes_2: int
    avg_depth_1: float  # MCTS 为 None
    avg_depth_2: float


@dataclass
class AgentStats:
    """Agent汇总统计"""
    name: str
    wins: int
    losses: int
    draws: int
    games: int
    win_rate: float
    avg_score: float  # (胜 + 0.5*平) / 总局数
    total_time: float
    total_nodes: int
    total_moves: int
    avg_time_per_move: float
    avg_nodes_per_move: float
    avg_depth: float


class StatCollector:
    """统计信息收集器（包装Agent，自动收集统计）"""

    def __init__(self, agent, name):
        self.agent = agent
        self.name = name
        self.move_count = 0
        self.total_time = 0.0
        self.total_nodes = 0
        self.total_depth = 0.0
        self.agent_type = self._get_agent_type()  # 保留算法类型，用于统计收集
        self.color = None  # 存储颜色（'red'/'black'），不影响agent_type
        self._last_nodes = 0  # 记录上次节点数
        self._last_sims = 0   # 记录上次模拟次数

    def _get_agent_type(self):
        """获取Agent类型"""
        if isinstance(self.agent, ChessRandomAgent):
            return 'random'
        elif isinstance(self.agent, ChessMinimaxAgent):
            return 'minimax'
        elif isinstance(self.agent, ChessAlphaBetaAgent):
            return 'alphabeta'
        elif isinstance(self.agent, ChessMCTSAgent):
            return 'mcts'
        return 'unknown'

    def select_move(self, game_state: GameState):
        """包装select_move，收集统计信息"""
        start_time = time.time()

        # 调用原始agent的select_move
        # 注意：agent内部会在开始时重置计数器，所以我们在调用后直接读取
        move = self.agent.select_move(game_state)

        elapsed = time.time() - start_time

        # 收集统计
        self.move_count += 1
        self.total_time += elapsed

        if self.agent_type == 'random':
            self.total_nodes += 1  # random只评估1个局面

        elif self.agent_type in ['minimax', 'alphabeta']:
            nodes = getattr(self.agent, '_nodes', 0)
            self.total_nodes += nodes
            # 累计实际搜索深度
            self.total_depth += getattr(self.agent, '_reached_depth', 0)

        elif self.agent_type == 'mcts':
            sims = getattr(self.agent, '_simulations', 0)
            self.total_nodes += sims

        return move

    def get_avg_depth(self):
        """获取平均深度（MCTS返回N/A）"""
        if self.agent_type in ['mcts', 'random']:
            return None
        if self.move_count == 0:
            return 0.0
        return self.total_depth / self.move_count


def play_game(collector1, collector2, move_limit=200, verbose=False):
    """
    对弈一局

    Returns:
        GameStats: 单局统计信息
    """
    game = GameState.new_game()
    collectors = {Player.red: collector1, Player.black: collector2}
    move_count = 0

    while not game.is_over() and move_count < move_limit:
        collector = collectors[game.next_player]
        move = collector.select_move(game)
        game = game.apply_move(move)
        move_count += 1

        if verbose and move_count % 50 == 0:
            print(f"  Move {move_count}...")

    # 确定胜者
    winner = game.winner()
    if winner == Player.red:
        winner_str = 'agent1' if collector1.color == 'red' else 'agent2'
    elif winner == Player.black:
        winner_str = 'agent2' if collector1.color == 'red' else 'agent1'
    else:
        winner_str = 'draw'

    return GameStats(
        agent1_name=collector1.name,
        agent2_name=collector2.name,
        agent1_color='red',
        winner=winner_str,
        num_moves=move_count,
        move_count_1=collector1.move_count,
        move_count_2=collector2.move_count,
        total_time_1=collector1.total_time,
        total_time_2=collector2.total_time,
        total_nodes_1=collector1.total_nodes,
        total_nodes_2=collector2.total_nodes,
        avg_depth_1=collector1.get_avg_depth(),
        avg_depth_2=collector2.get_avg_depth(),
    )


def run_round_robin(agents_config: Dict[str, Any], games_per_pair: int,
                    output_dir: str, verbose: bool = True,
                    pair_filter: List[int] = None):
    """
    运行循环赛

    Args:
        agents_config: Agent配置字典 {name: (type, kwargs)}
        games_per_pair: 每对局数
        output_dir: 输出目录
        verbose: 是否输出详细信息
        pair_filter: 只跑指定编号的对（1-based），None表示全跑
    """
    # 创建agents
    agents = {}
    for name, (agent_class, kwargs) in agents_config.items():
        agents[name] = agent_class(**kwargs)

    agent_names = list(agents.keys())
    all_stats = []
    agent_summary = defaultdict(lambda: {
        'wins': 0, 'losses': 0, 'draws': 0,
        'total_time': 0.0, 'total_nodes': 0, 'total_moves': 0,
        'total_depth': 0.0, 'depth_count': 0
    })

    # 每对agent对战
    total_pairs = len(agent_names) * (len(agent_names) - 1) // 2
    pair_idx = 0

    for i in range(len(agent_names)):
        for j in range(i + 1, len(agent_names)):
            pair_idx += 1
            name1, name2 = agent_names[i], agent_names[j]

            if verbose:
                print(f"\n=== Pair {pair_idx}/{total_pairs}: {name1} vs {name2} ===")

            # 跳过不在过滤列表中的对
            if pair_filter is not None and pair_idx not in pair_filter:
                if verbose:
                    print(f"  (skipped)")
                continue

            for g in range(games_per_pair):
                # 交换先后手
                if g % 2 == 0:
                    agent1, agent2 = agents[name1], agents[name2]
                    collector1 = StatCollector(agent1, name1)
                    collector2 = StatCollector(agent2, name2)
                    # 设置颜色（使用color字段，不覆盖agent_type）
                    collector1.color = 'red'
                    collector2.color = 'black'
                else:
                    agent1, agent2 = agents[name2], agents[name1]
                    collector1 = StatCollector(agent1, name2)
                    collector2 = StatCollector(agent2, name1)
                    collector1.color = 'red'
                    collector2.color = 'black'

                red_name = collector1.name
                black_name = collector2.name
                if verbose:
                    print(f"  Game {g+1}/{games_per_pair}: {red_name}(红) vs {black_name}(黑) ...", end='', flush=True)

                # 对弈
                game_stats = play_game(collector1, collector2, verbose=False)
                all_stats.append(game_stats)

                # 更新汇总统计
                _update_summary(agent_summary, game_stats)

                if verbose:
                    winner = game_stats.winner
                    if winner == 'agent1':
                        winner_label = f"{game_stats.agent1_name} 胜"
                    elif winner == 'agent2':
                        winner_label = f"{game_stats.agent2_name} 胜"
                    else:
                        winner_label = "平局"
                    print(f" {winner_label} ({game_stats.num_moves}步, "
                          f"{game_stats.total_time_1 + game_stats.total_time_2:.0f}s)")

    # 计算汇总
    agent_stats_list = []
    for name, summary in agent_summary.items():
        games = summary['wins'] + summary['losses'] + summary['draws']
        win_rate = summary['wins'] / games if games > 0 else 0
        avg_score = (summary['wins'] + 0.5 * summary['draws']) / games if games > 0 else 0
        avg_depth = (summary['total_depth'] / summary['depth_count']
                     if summary['depth_count'] > 0 else 0)

        agent_stats_list.append(AgentStats(
            name=name,
            wins=summary['wins'],
            losses=summary['losses'],
            draws=summary['draws'],
            games=games,
            win_rate=win_rate,
            avg_score=avg_score,
            total_time=summary['total_time'],
            total_nodes=summary['total_nodes'],
            total_moves=summary['total_moves'],
            avg_time_per_move=summary['total_time'] / summary['total_moves']
                                 if summary['total_moves'] > 0 else 0,
            avg_nodes_per_move=summary['total_nodes'] / summary['total_moves']
                                  if summary['total_moves'] > 0 else 0,
            avg_depth=avg_depth,
        ))

    # 保存结果
    os.makedirs(output_dir, exist_ok=True)

    # CSV: 详细对局数据
    csv_path = os.path.join(output_dir, 'game_details.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=GameStats.__dataclass_fields__.keys())
        writer.writeheader()
        for stats in all_stats:
            writer.writerow(asdict(stats))

    # JSON: 汇总统计
    json_path = os.path.join(output_dir, 'summary.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump([asdict(s) for s in agent_stats_list], f, indent=2, ensure_ascii=False)

    if verbose:
        print(f"\n=== Results saved to {output_dir} ===")

    return agent_stats_list, all_stats


def _update_summary(summary, game_stats):
    """更新汇总统计"""
    # 直接从 game_stats 读取实际的 agent 名字（避免 name1/name2 顺序与 collector 顺序不一致的问题）
    a1_name = game_stats.agent1_name
    a2_name = game_stats.agent2_name

    # 更新时间/节点/步数/深度统计
    for name, time, nodes, moves, depth in [
        (a1_name, game_stats.total_time_1, game_stats.total_nodes_1,
         game_stats.move_count_1, game_stats.avg_depth_1),
        (a2_name, game_stats.total_time_2, game_stats.total_nodes_2,
         game_stats.move_count_2, game_stats.avg_depth_2),
    ]:
        summary[name]['total_time'] += time
        summary[name]['total_nodes'] += nodes
        summary[name]['total_moves'] += moves
        if depth is not None:
            summary[name]['total_depth'] += depth * moves
            summary[name]['depth_count'] += moves

    # 胜负统计
    winner = game_stats.winner
    if winner == 'draw':
        summary[a1_name]['draws'] += 1
        summary[a2_name]['draws'] += 1
    elif winner == 'agent1':
        summary[a1_name]['wins'] += 1
        summary[a2_name]['losses'] += 1
    else:  # agent2
        summary[a2_name]['wins'] += 1
        summary[a1_name]['losses'] += 1


def print_results(agent_stats: List[AgentStats]):
    """打印结果表格"""
    print("\n" + "=" * 80)
    print("TOURNAMENT RESULTS")
    print("=" * 80)

    # 对弈结果矩阵
    print("\n┌─────────────┬──────┬──────┬──────┬────────┐")
    print("│   Agent     │ Win  │ Draw │ Loss │ WinRate│")
    print("├─────────────┼──────┼──────┼──────┼────────┤")
    for stats in sorted(agent_stats, key=lambda s: s.win_rate, reverse=True):
        print(f"│ {stats.name:<11} │ {stats.wins:4d} │ "
              f"{stats.draws:4d} │ {stats.losses:4d} │ "
              f"{stats.win_rate:6.1%} │")
    print("└─────────────┴──────┴──────┴──────┴────────┘")

    # 性能指标
    print("\n┌─────────────┬───────────┬───────────┬──────────┐")
    print("│   Agent     │ Time/Move │ Nodes/Move│ Depth    │")
    print("├─────────────┼───────────┼───────────┼──────────┤")
    for stats in agent_stats:
        depth_str = f"{stats.avg_depth:.1f}" if stats.avg_depth > 0 else "N/A"
        print(f"│ {stats.name:<11} │ {stats.avg_time_per_move:9.2f}s │ "
              f"{stats.avg_nodes_per_move:9.0f} │ {depth_str:>8} │")
    print("└─────────────┴───────────┴───────────┴──────────┘")


def main():
    parser = argparse.ArgumentParser(description="搜索算法对比实验：循环赛")
    parser.add_argument("--games", type=int, default=20,
                       help="每对agent对弈局数（默认20）")
    parser.add_argument("--output", type=str, default="experiments/results",
                       help="输出目录（默认experiments/results）")
    parser.add_argument("--quick", action="store_true",
                       help="快速模式：每对1局，1s时间限制")
    parser.add_argument("--quiet", action="store_true",
                       help="静默模式：减少输出")
    parser.add_argument("--pairs", type=str, default=None,
                       help="只跑指定对，逗号分隔（如 --pairs 1,2,3）。"
                            "共6对：1=Random-Minimax, 2=Random-AlphaBeta, "
                            "3=Random-MCTS, 4=Minimax-AlphaBeta, "
                            "5=Minimax-MCTS, 6=AlphaBeta-MCTS")

    args = parser.parse_args()

    # 快速模式
    if args.quick:
        args.games = 1

    # 解析 --pairs
    pair_filter = None
    if args.pairs:
        pair_filter = [int(x) for x in args.pairs.split(',')]

    # 固定随机种子（可重复性）
    random.seed(42)

    # Agent配置
    # 所有Agent使用相同的评估函数evaluate()，控制变量一致
    # quick模式用1s时间限制加速测试，正式实验用5s
    time_limit = 1.0 if args.quick else 5.0
    agents_config = {
        'Random': (ChessRandomAgent, {}),
        'Minimax': (ChessMinimaxAgent, {'time_limit': time_limit, 'max_depth': 3, 'verbose': False}),
        'AlphaBeta': (ChessAlphaBetaAgent, {'time_limit': time_limit, 'max_depth': 6, 'verbose': False}),
        'MCTS': (ChessMCTSAgent, {'time_limit': time_limit, 'verbose': False}),
    }

    print(f"\n=== 搜索算法对比实验 ===")
    print(f"Agents: {', '.join(agents_config.keys())}")
    print(f"Games per pair: {args.games}")
    if pair_filter:
        print(f"Running pairs: {pair_filter}")
    print(f"Output: {args.output}/")

    # 运行循环赛
    agent_stats, _ = run_round_robin(
        agents_config, args.games, args.output,
        verbose=not args.quiet, pair_filter=pair_filter
    )

    # 打印结果
    if not args.quiet:
        print_results(agent_stats)


if __name__ == "__main__":
    main()
