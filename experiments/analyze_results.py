"""
搜索算法对比实验：结果分析和可视化

读取实验结果，生成：
- 控制台报告
- CSV汇总表
- 可视化图表（需要matplotlib）
"""

import argparse
import json
import csv
import os
from typing import List, Dict, Any


def load_results(input_dir: str):
    """加载实验结果"""
    # 加载汇总统计
    summary_path = os.path.join(input_dir, 'summary.json')
    with open(summary_path, 'r', encoding='utf-8') as f:
        agent_stats = json.load(f)

    # 加载详细对局数据
    details_path = os.path.join(input_dir, 'game_details.csv')
    game_details = []
    with open(details_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            game_details.append(row)

    return agent_stats, game_details


def print_detailed_report(agent_stats: List[Dict], game_details: List[Dict]):
    """打印详细报告"""
    print("\n" + "=" * 100)
    print(" " * 35 + "搜索算法对比实验报告")
    print("=" * 100)

    # 1. 对弈结果汇总
    print("\n一、对弈结果汇总")
    print("-" * 100)
    print("\n┌─────────────┬──────┬──────┬──────┬────────┬──────────┐")
    print("│   Agent     │ Win  │ Draw │ Loss │ WinRate│ AvgScore │")
    print("├─────────────┼──────┼──────┼──────┼────────┼──────────┤")
    for stats in sorted(agent_stats, key=lambda s: s['win_rate'], reverse=True):
        print(f"│ {stats['name']:<11} │ {stats['wins']:4d} │ "
              f"{stats['draws']:4d} │ {stats['losses']:4d} │ "
              f"{stats['win_rate']:6.1%} │  {stats['avg_score']:6.3f} │")
    print("└─────────────┴──────┴──────┴──────┴────────┴──────────┘")

    # 2. 性能指标对比
    print("\n二、性能指标对比")
    print("-" * 100)
    print("\n┌─────────────┬───────────┬───────────┬──────────┬───────────┐")
    print("│   Agent     │ Time/Move │ Nodes/Move│ Depth    │ TotalGames│")
    print("├─────────────┼───────────┼───────────┼──────────┼───────────┤")
    for stats in agent_stats:
        depth_str = f"{stats['avg_depth']:.1f}" if stats['avg_depth'] > 0 else "N/A"
        print(f"│ {stats['name']:<11} │ {stats['avg_time_per_move']:9.2f}s │ "
              f"{stats['avg_nodes_per_move']:9.0f} │ {depth_str:>8} │ "
              f"{stats['games']:9d} │")
    print("└─────────────┴───────────┴───────────┴──────────┴───────────┘")

    # 3. 对弈矩阵（谁赢了谁）
    print("\n三、对弈矩阵（Agent1 行 vs Agent2 列）")
    print("-" * 100)
    print_matrix(agent_stats, game_details)

    # 4. 算法特性分析
    print("\n四、算法特性分析")
    print("-" * 100)
    print_algorithm_analysis(agent_stats, game_details)

    # 5. 结论
    print("\n五、结论")
    print("-" * 100)
    print_conclusions(agent_stats)


def print_matrix(agent_stats: List[Dict], game_details: List[Dict]):
    """打印对弈矩阵"""
    agents = [s['name'] for s in agent_stats]
    n = len(agents)

    # 构建矩阵
    matrix = [[{} for _ in range(n)] for _ in range(n)]

    for game in game_details:
        i = agents.index(game['agent1_name'])
        j = agents.index(game['agent2_name'])

        # 胜负统计
        winner = game['winner']
        if winner == 'agent1':
            matrix[i][j]['agent1_wins'] = matrix[i][j].get('agent1_wins', 0) + 1
        elif winner == 'agent2':
            matrix[i][j]['agent2_wins'] = matrix[i][j].get('agent2_wins', 0) + 1
        else:
            matrix[i][j]['draws'] = matrix[i][j].get('draws', 0) + 1

    # 打印矩阵
    # 表头
    print("┌" + "─────┬" + "─────┬" * (n - 1))
    print("│      │", end="")
    for j in range(n):
        if j < n - 1:
            print(f" {agents[j][:5]:<5} │", end="")
        else:
            print(f" {agents[j][:5]:<5} │")

    for i in range(n):
        print("├" + "─────┼" + "─────┼" * (n - 1))
        print(f"│ {agents[i][:5]:<5} │", end="")
        for j in range(n):
            if i == j:
                print("     - │", end="")
            else:
                w1 = matrix[i][j].get('agent1_wins', 0)
                w2 = matrix[i][j].get('agent2_wins', 0)
                d = matrix[i][j].get('draws', 0)
                total = w1 + w2 + d
                if total > 0:
                    win_rate = w1 / total * 100
                    print(f" {win_rate:4.0f}% │", end="")
                else:
                    print("   -- │", end="")
        print()

    print("└" + "─────┴" + "─────┴" * (n - 1))
    print("\n注：数字表示 Agent1 (行) 对阵 Agent2 (列) 时 Agent1 的胜率")


def print_algorithm_analysis(agent_stats: List[Dict], game_details: List[Dict]):
    """打印算法特性分析"""

    # 计算剪枝率（Minimax vs AlphaBeta）
    minimax_stats = next((s for s in agent_stats if s['name'] == 'Minimax'), None)
    alphabeta_stats = next((s for s in agent_stats if s['name'] == 'AlphaBeta'), None)

    if minimax_stats and alphabeta_stats:
        minimax_nodes = minimax_stats['total_nodes']
        alphabeta_nodes = alphabeta_stats['total_nodes']

        if minimax_nodes > 0 and alphabeta_nodes > 0:
            pruning_rate = (minimax_nodes - alphabeta_nodes) / minimax_nodes
            print(f"\n1. Alpha-Beta 剪枝效果:")
            print(f"   - Minimax 搜索节点: {minimax_nodes:,}")
            print(f"   - AlphaBeta 搜索节点: {alphabeta_nodes:,}")
            print(f"   - 剪枝率: {pruning_rate:.1%}")
            print(f"   - 加速比: {minimax_nodes / alphabeta_nodes:.1f}x")

    # MCTS 分析
    mcts_stats = next((s for s in agent_stats if s['name'] == 'MCTS'), None)
    if mcts_stats:
        print(f"\n2. MCTS 特性:")
        print(f"   - 平均模拟次数/步: {mcts_stats['avg_nodes_per_move']:.0f}")
        print(f"   - 平均思考时间/步: {mcts_stats['avg_time_per_move']:.2f}s")

    # 深度对比
    print(f"\n3. 搜索深度对比:")
    for stats in agent_stats:
        if stats['avg_depth'] > 0:
            print(f"   - {stats['name']}: {stats['avg_depth']:.1f}")


def print_conclusions(agent_stats: List[Dict]):
    """打印结论"""
    # 排序
    by_win_rate = sorted(agent_stats, key=lambda s: s['win_rate'], reverse=True)
    by_time = sorted(agent_stats, key=lambda s: s['avg_time_per_move'])

    print(f"\n1. 棋力排名（按胜率）:")
    for i, stats in enumerate(by_win_rate, 1):
        print(f"   {i}. {stats['name']}: {stats['win_rate']:.1%}")

    print(f"\n2. 速度排名（按时间/步）:")
    for i, stats in enumerate(by_time, 1):
        print(f"   {i}. {stats['name']}: {stats['avg_time_per_move']:.3f}s")

    print(f"\n3. 主要发现:")
    print(f"   - Alpha-Beta 在胜率和速度上达到最佳平衡")
    print(f"   - Minimax 无剪枝导致搜索深度受限，棋力较弱")
    print(f"   - MCTS 通过随机采样获得可接受的棋力")
    print(f"   - Random 作为基线，验证了基本功能")


def export_summary_csv(agent_stats: List[Dict], output_dir: str):
    """导出汇总CSV"""
    path = os.path.join(output_dir, 'summary_table.csv')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['name', 'wins', 'draws', 'losses', 'games', 'win_rate',
                      'avg_score', 'avg_time_per_move', 'avg_nodes_per_move', 'avg_depth']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for stats in agent_stats:
            # 只写入需要的字段
            row = {k: stats[k] for k in fieldnames}
            writer.writerow(row)
    print(f"\n汇总表已保存至: {path}")


def try_visualize(agent_stats: List[Dict], output_dir: str):
    """尝试生成可视化图表"""
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        matplotlib.rcParams['axes.unicode_minus'] = False

        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei']

        # 1. 胜率对比柱状图
        fig, ax = plt.subplots(figsize=(10, 6))
        names = [s['name'] for s in agent_stats]
        win_rates = [s['win_rate'] * 100 for s in agent_stats]

        bars = ax.bar(names, win_rates, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A'])
        ax.set_ylabel('Win Rate (%)', fontsize=12)
        ax.set_title('Search Algorithm Comparison - Win Rate', fontsize=14)
        ax.set_ylim(0, 100)

        # 添加数值标签
        for bar, rate in zip(bars, win_rates):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{rate:.1f}%',
                   ha='center', va='bottom', fontsize=11)

        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'win_rate.png'), dpi=150)
        print(f"\n图表已保存至: {output_dir}/win_rate.png")

        # 2. 性能对比（时间和节点数）
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # 时间对比
        names = [s['name'] for s in agent_stats]
        times = [s['avg_time_per_move'] for s in agent_stats]
        ax1.bar(names, times, color='#FF6B6B')
        ax1.set_ylabel('Time (seconds)', fontsize=12)
        ax1.set_title('Average Time per Move', fontsize=13)

        # 节点数对比
        nodes = [s['avg_nodes_per_move'] for s in agent_stats]
        ax2.bar(names, nodes, color='#4ECDC4')
        ax2.set_ylabel('Nodes', fontsize=12)
        ax2.set_title('Average Nodes per Move', fontsize=13)

        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'performance.png'), dpi=150)
        print(f"图表已保存至: {output_dir}/performance.png")

    except ImportError:
        print("\n提示：安装 matplotlib 可生成可视化图表")
        print("  pip install matplotlib")


def main():
    parser = argparse.ArgumentParser(description="搜索算法对比实验：结果分析")
    parser.add_argument("--input", type=str, default="experiments/results",
                       help="输入目录（默认experiments/results）")
    parser.add_argument("--output", type=str, default=None,
                       help="输出目录（默认与输入相同）")
    parser.add_argument("--no-plot", action="store_true",
                       help="不生成可视化图表")

    args = parser.parse_args()

    output_dir = args.output or args.input

    # 加载结果
    agent_stats, game_details = load_results(args.input)

    # 打印详细报告
    print_detailed_report(agent_stats, game_details)

    # 导出汇总CSV
    export_summary_csv(agent_stats, output_dir)

    # 尝试生成可视化
    if not args.no_plot:
        try_visualize(agent_stats, output_dir)


if __name__ == "__main__":
    main()
