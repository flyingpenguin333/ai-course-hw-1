"""
合并多个容器的实验结果

用法：
    python experiments/merge_results.py --inputs dir1 dir2 dir3 --output experiments/results

每个输入目录需包含 game_details.csv，脚本会合并所有对局数据，
重新计算汇总统计，输出到 --output 目录。
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.run_tournament import GameStats, AgentStats, _update_summary


def load_game_details(csv_path):
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            # 类型转换
            rows.append(GameStats(
                agent1_name=row['agent1_name'],
                agent2_name=row['agent2_name'],
                agent1_color=row['agent1_color'],
                winner=row['winner'],
                num_moves=int(row['num_moves']),
                total_time_1=float(row['total_time_1']),
                total_time_2=float(row['total_time_2']),
                total_nodes_1=int(row['total_nodes_1']),
                total_nodes_2=int(row['total_nodes_2']),
                avg_depth_1=float(row['avg_depth_1']) if row['avg_depth_1'] not in ('None', '') else None,
                avg_depth_2=float(row['avg_depth_2']) if row['avg_depth_2'] not in ('None', '') else None,
            ))
    return rows


def recompute_summary(all_stats):
    agent_summary = defaultdict(lambda: {
        'wins': 0, 'losses': 0, 'draws': 0,
        'total_time': 0.0, 'total_nodes': 0, 'total_moves': 0,
        'total_depth': 0.0, 'depth_count': 0
    })

    for gs in all_stats:
        name1, name2 = gs.agent1_name, gs.agent2_name
        agent1_is_red = (gs.agent1_color == 'red')

        for name, t, n in [(name1, gs.total_time_1, gs.total_nodes_1),
                           (name2, gs.total_time_2, gs.total_nodes_2)]:
            agent_summary[name]['total_time'] += t
            agent_summary[name]['total_nodes'] += n
            agent_summary[name]['total_moves'] += gs.num_moves

        winner = gs.winner
        red_name = name1 if agent1_is_red else name2
        black_name = name2 if agent1_is_red else name1

        if winner == 'draw':
            agent_summary[red_name]['draws'] += 1
            agent_summary[black_name]['draws'] += 1
        elif winner == 'agent1':
            winner_name = name1
            loser_name = name2
            agent_summary[winner_name]['wins'] += 1
            agent_summary[loser_name]['losses'] += 1
        else:
            winner_name = name2
            loser_name = name1
            agent_summary[winner_name]['wins'] += 1
            agent_summary[loser_name]['losses'] += 1

    agent_stats_list = []
    for name, s in agent_summary.items():
        games = s['wins'] + s['losses'] + s['draws']
        win_rate = s['wins'] / games if games > 0 else 0
        avg_score = (s['wins'] + 0.5 * s['draws']) / games if games > 0 else 0
        avg_depth = s['total_depth'] / s['depth_count'] if s['depth_count'] > 0 else 0

        agent_stats_list.append(AgentStats(
            name=name,
            wins=s['wins'], losses=s['losses'], draws=s['draws'], games=games,
            win_rate=win_rate, avg_score=avg_score,
            total_time=s['total_time'], total_nodes=s['total_nodes'],
            total_moves=s['total_moves'],
            avg_time_per_move=s['total_time'] / s['total_moves'] if s['total_moves'] > 0 else 0,
            avg_nodes_per_move=s['total_nodes'] / s['total_moves'] if s['total_moves'] > 0 else 0,
            avg_depth=avg_depth,
        ))

    return agent_stats_list


def main():
    parser = argparse.ArgumentParser(description="合并多个容器的实验结果")
    parser.add_argument("--inputs", nargs='+', required=True,
                        help="输入目录列表（每个目录含 game_details.csv）")
    parser.add_argument("--output", type=str, required=True,
                        help="合并结果输出目录")
    args = parser.parse_args()

    all_stats = []
    for d in args.inputs:
        csv_path = os.path.join(d, 'game_details.csv')
        if not os.path.exists(csv_path):
            print(f"[警告] 找不到 {csv_path}，跳过")
            continue
        rows = load_game_details(csv_path)
        all_stats.extend(rows)
        print(f"Loaded {len(rows)} games from {d}")

    print(f"Total: {len(all_stats)} games")

    agent_stats = recompute_summary(all_stats)

    os.makedirs(args.output, exist_ok=True)

    csv_out = os.path.join(args.output, 'game_details.csv')
    with open(csv_out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=GameStats.__dataclass_fields__.keys())
        writer.writeheader()
        for gs in all_stats:
            writer.writerow(asdict(gs))

    json_out = os.path.join(args.output, 'summary.json')
    with open(json_out, 'w', encoding='utf-8') as f:
        json.dump([asdict(s) for s in agent_stats], f, indent=2, ensure_ascii=False)

    print(f"Merged results saved to {args.output}/")

    # 打印简要结果
    print("\n=== Merged Results ===")
    for s in sorted(agent_stats, key=lambda x: x.win_rate, reverse=True):
        depth_str = f"{s.avg_depth:.1f}" if s.avg_depth else "N/A"
        print(f"  {s.name}: {s.wins}W {s.draws}D {s.losses}L  win_rate={s.win_rate:.1%}  "
              f"nodes/move={s.avg_nodes_per_move:.0f}  depth={depth_str}")


if __name__ == "__main__":
    main()
