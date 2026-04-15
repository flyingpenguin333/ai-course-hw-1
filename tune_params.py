"""
自动调参脚本：简化版自适应遗传算法（AGA）。

参考 PDF03（东北大学，2005）的自适应遗传算法，通过自我对弈锦标赛
自动优化评估函数参数。

用法：
    python tune_params.py
    python tune_params.py --pop 16 --gen 50 --depth 3 --workers 4
"""

import argparse
import copy
import json
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import fields

from cchess import GameState, Player
from cchess.evaluate import EvalParams, DEFAULT_PARAMS, evaluate
from agents.chess_alphabeta_agent import ChessAlphaBetaAgent

# ── 可调参数范围（EVAL7：25个权重）───────────────────────
PARAM_RANGES = {
    # MATL: 子力价值 (7个)
    'w_chariot':      (600, 1200),
    'w_cannon':       (300, 600),
    'w_horse':        (300, 600),
    'w_advisor':      (100, 350),
    'w_elephant':     (100, 350),
    'w_pawn':         (50, 200),
    'w_pawn_crossed': (50, 200),
    # MOB: 机动性 (7个)
    'w_mob_chariot':  (0.0, 5.0),
    'w_mob_cannon':   (0.0, 5.0),
    'w_mob_horse':    (0.0, 5.0),
    'w_mob_advisor':  (0.0, 2.0),
    'w_mob_elephant': (0.0, 2.0),
    'w_mob_pawn':     (0.0, 2.0),
    'w_mob_general':  (0.0, 1.0),
    # AKA: 攻击将帅相邻格 (5个)
    'w_aka_chariot':  (0.0, 20.0),
    'w_aka_knight':   (0.0, 20.0),
    'w_aka_cannon':   (0.0, 20.0),
    'w_aka_advisor':  (0.0, 10.0),
    'w_aka_elephant': (0.0, 10.0),
    # SPC: 安全潜在将军 (5个)
    'w_spc_chariot':  (0.0, 30.0),
    'w_spc_knight':   (0.0, 30.0),
    'w_spc_cannon':   (0.0, 30.0),
    'w_spc_advisor':  (0.0, 15.0),
    'w_spc_elephant': (0.0, 15.0),
    # COP: 追逐 (1个)
    'w_chase':        (0.0, 10.0),
}

# ── AGA 自适应参数（PDF03 公式）──────────────────────
PC1, PC2 = 0.9, 0.6   # 交叉率范围
PM1, PM2 = 0.1, 0.001  # 变异率范围


def random_params():
    """生成随机参数个体。"""
    d = {}
    for name, (lo, hi) in PARAM_RANGES.items():
        if isinstance(lo, float):
            d[name] = random.uniform(lo, hi)
        else:
            d[name] = random.randint(lo, hi)
    return EvalParams.from_dict(d)


def mutate(params, strength=0.15):
    """高斯变异：每个参数以一定概率扰动 ±strength 比例。"""
    d = params.to_dict()
    for name, (lo, hi) in PARAM_RANGES.items():
        if random.random() < 0.3:  # 30%概率变异该参数
            val = d[name]
            spread = (hi - lo) * strength
            new_val = val + random.gauss(0, spread)
            if isinstance(lo, float):
                d[name] = max(lo, min(hi, new_val))
            else:
                d[name] = max(lo, min(hi, int(round(new_val))))
    return EvalParams.from_dict(d)


def crossover(p1, p2):
    """均匀交叉（PDF03 3.2节）。"""
    d1, d2 = p1.to_dict(), p2.to_dict()
    child = {}
    for name in PARAM_RANGES:
        child[name] = d1[name] if random.random() < 0.5 else d2[name]
    return EvalParams.from_dict(child)


def adaptive_pc_pm(fitness, f_avg, f_max):
    """自适应交叉率和变异率（PDF03 公式）。"""
    if f_max == f_avg:
        return PC1, PM1
    if fitness >= f_avg:
        pc = PC1 - (PC1 - PC2) * (fitness - f_avg) / (f_max - f_avg)
    else:
        pc = PC1
    if fitness >= f_max:
        pm = PM2
    else:
        pm = PM1 - (PM1 - PM2) * (f_max - fitness) / (f_max - f_avg)
    return pc, pm


# ── 对弈函数（可被 ProcessPoolExecutor 调用）────────
def play_match(params1_dict, params2_dict, depth, move_limit):
    """两个参数集对弈一局，返回 (1方胜=1, 2方胜=-1, 平=0)。"""
    p1 = EvalParams.from_dict(params1_dict)
    p2 = EvalParams.from_dict(params2_dict)
    a1 = ChessAlphaBetaAgent(time_limit=999, max_depth=depth, eval_params=p1, verbose=False)
    a2 = ChessAlphaBetaAgent(time_limit=999, max_depth=depth, eval_params=p2, verbose=False)

    game = GameState.new_game()
    agents = {Player.red: a1, Player.black: a2}
    for _ in range(move_limit):
        if game.is_over():
            break
        move = agents[game.next_player].select_move(game)
        game = game.apply_move(move)

    winner = game.winner()
    if winner == Player.red:
        return 1
    elif winner == Player.black:
        return -1
    return 0


# ── PLACEHOLDER_MAIN ──


def run_tournament(population, depth, move_limit, games_per_match, workers):
    """循环赛：每对个体对弈，返回每个个体的胜率。"""
    n = len(population)
    scores = [0.0] * n
    total_games = [0] * n
    tasks = []

    for i in range(n):
        for j in range(i + 1, n):
            for g in range(games_per_match):
                if g % 2 == 0:
                    tasks.append((population[i].to_dict(), population[j].to_dict(), i, j, False))
                else:
                    tasks.append((population[j].to_dict(), population[i].to_dict(), i, j, True))

    # 尝试并行，失败则串行
    results = []
    if workers > 1:
        try:
            with ProcessPoolExecutor(max_workers=workers) as executor:
                futs = []
                for p1d, p2d, i, j, sw in tasks:
                    futs.append((executor.submit(play_match, p1d, p2d, depth, move_limit), i, j, sw))
                for fut, i, j, sw in futs:
                    results.append((fut.result(), i, j, sw))
        except Exception:
            print("[WARN] multiprocessing failed, falling back to sequential")
            results = []
            workers = 1

    if workers <= 1:
        for p1d, p2d, i, j, sw in tasks:
            r = play_match(p1d, p2d, depth, move_limit)
            results.append((r, i, j, sw))

    for result, i, j, swapped in results:
        if swapped:
            result = -result
        if result == 1:
            scores[i] += 1
        elif result == -1:
            scores[j] += 1
        else:
            scores[i] += 0.5
            scores[j] += 0.5
        total_games[i] += 1
        total_games[j] += 1

    fitness = [scores[i] / max(total_games[i], 1) for i in range(n)]
    return fitness


def evolve(population, fitness):
    """一代进化：选择 + 交叉 + 变异。"""
    n = len(population)
    f_avg = sum(fitness) / n
    f_max = max(fitness)

    # 精英保留：最好的2个直接进入下一代
    ranked = sorted(range(n), key=lambda i: fitness[i], reverse=True)
    new_pop = [population[ranked[0]], population[ranked[1]]]

    # 锦标赛选择 + 交叉 + 变异填充剩余
    while len(new_pop) < n:
        # 锦标赛选择两个父代（3选1）
        parent1 = _tournament_select(population, fitness, k=3)
        parent2 = _tournament_select(population, fitness, k=3)

        pc, pm = adaptive_pc_pm(
            max(fitness[population.index(parent1)],
                fitness[population.index(parent2)]),
            f_avg, f_max)

        if random.random() < pc:
            child = crossover(parent1, parent2)
        else:
            child = copy.deepcopy(parent1)

        if random.random() < pm:
            child = mutate(child)

        new_pop.append(child)

    return new_pop


def _tournament_select(population, fitness, k=3):
    """k-锦标赛选择。"""
    candidates = random.sample(list(enumerate(fitness)), min(k, len(fitness)))
    best_idx = max(candidates, key=lambda x: x[1])[0]
    return population[best_idx]


def main():
    parser = argparse.ArgumentParser(description="象棋评估函数自动调参")
    parser.add_argument("--pop", type=int, default=12, help="种群大小")
    parser.add_argument("--gen", type=int, default=30, help="代数")
    parser.add_argument("--depth", type=int, default=3, help="搜索深度")
    parser.add_argument("--games", type=int, default=4, help="每对个体对弈局数")
    parser.add_argument("--move-limit", type=int, default=150, help="每局步数上限")
    parser.add_argument("--workers", type=int, default=4, help="并行进程数")
    args = parser.parse_args()

    out_dir = "tuning_results"
    os.makedirs(out_dir, exist_ok=True)

    # 初始化种群：默认参数 + 随机个体
    population = [DEFAULT_PARAMS]
    for _ in range(args.pop - 1):
        population.append(random_params())

    best_ever = DEFAULT_PARAMS
    best_ever_fitness = 0.0

    print(f"=== AGA 自动调参 ===")
    print(f"种群={args.pop}, 代数={args.gen}, 深度={args.depth}, "
          f"每对局数={args.games}, 进程={args.workers}")
    print()

    for gen in range(1, args.gen + 1):
        t0 = time.time()
        fitness = run_tournament(
            population, args.depth, args.move_limit, args.games, args.workers)
        elapsed = time.time() - t0

        best_idx = max(range(len(fitness)), key=lambda i: fitness[i])
        best_params = population[best_idx]
        best_fit = fitness[best_idx]
        avg_fit = sum(fitness) / len(fitness)

        if best_fit > best_ever_fitness:
            best_ever = best_params
            best_ever_fitness = best_fit

        # 保存本代最佳
        gen_path = os.path.join(out_dir, f"gen_{gen:03d}.json")
        best_params.save(gen_path)

        # 保存全局最优
        best_ever.save(os.path.join(out_dir, "best_params.json"))

        print(f"Gen {gen:3d}/{args.gen} | "
              f"best={best_fit:.3f} avg={avg_fit:.3f} | "
              f"time={elapsed:.1f}s | "
              f"chariot={best_params.w_chariot} "
              f"cannon={best_params.w_cannon} "
              f"horse={best_params.w_horse}")

        # 进化
        population = evolve(population, fitness)

    print(f"\n=== 调参完成 ===")
    print(f"全局最优胜率: {best_ever_fitness:.3f}")
    print(f"最优参数: {best_ever.to_dict()}")
    print(f"已保存至 {out_dir}/best_params.json")


if __name__ == "__main__":
    main()
