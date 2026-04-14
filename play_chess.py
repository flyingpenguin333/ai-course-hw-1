"""
中国象棋对弈测试脚本。

用法：
    python play_chess.py --agent1 random --agent2 random
    python play_chess.py --agent1 random --agent2 random --games 10 --quiet
"""

import argparse
import random
import time

from cchess import GameState, Player, Point, PieceType

PIECE_CHARS = {
    (Player.red, PieceType.GENERAL):  '帅',
    (Player.red, PieceType.ADVISOR):  '仕',
    (Player.red, PieceType.ELEPHANT): '相',
    (Player.red, PieceType.HORSE):    '馬',
    (Player.red, PieceType.CHARIOT):  '車',
    (Player.red, PieceType.CANNON):   '砲',
    (Player.red, PieceType.PAWN):     '兵',
    (Player.black, PieceType.GENERAL):  '将',
    (Player.black, PieceType.ADVISOR):  '士',
    (Player.black, PieceType.ELEPHANT): '象',
    (Player.black, PieceType.HORSE):    '马',
    (Player.black, PieceType.CHARIOT):  '车',
    (Player.black, PieceType.CANNON):   '炮',
    (Player.black, PieceType.PAWN):     '卒',
}


def make_agent(name):
    if name == "random":
        from agents.chess_random_agent import ChessRandomAgent
        agent = ChessRandomAgent()
        return agent.select_move
    raise ValueError(f"未知智能体: {name}")


AGENT_NAMES = ["random"]


def print_board(game_state):
    board = game_state.board
    print("   ", end="")
    for c in range(board.NUM_COLS):
        print(f" {c} ", end="")
    print()

    for r in range(board.NUM_ROWS - 1, -1, -1):
        print(f"{r:2} ", end="")
        for c in range(board.NUM_COLS):
            piece = board.get(Point(r, c))
            if piece is None:
                if r == 4 or r == 5:
                    print(" ~ ", end="")  # 楚河汉界
                else:
                    print(" . ", end="")
            else:
                ch = PIECE_CHARS[(piece.player, piece.piece_type)]
                print(f" {ch}", end="")
        print()
    print()


def play_game(agent1_fn, agent2_fn, verbose=True):
    game = GameState.new_game()
    agents = {Player.red: agent1_fn, Player.black: agent2_fn}
    move_count = 0
    start_time = time.time()

    while not game.is_over():
        if verbose:
            print(f"\n=== 第 {move_count + 1} 步, {game.next_player.name} 方 ===")
            print_board(game)

        move = agents[game.next_player](game)
        if verbose:
            print(f"走法: {move}")

        game = game.apply_move(move)
        move_count += 1

        if move_count > 300:
            print("[WARN] 步数过多，强制结束")
            break

    duration = time.time() - start_time
    winner = game.winner()

    if verbose:
        print("\n=== 终局 ===")
        print_board(game)
        if winner:
            print(f"胜者: {winner.name}")
        else:
            print("平局/未决")

    return winner, move_count, duration


def main():
    parser = argparse.ArgumentParser(description="中国象棋 AI 对弈")
    parser.add_argument("--agent1", choices=AGENT_NAMES, default="random", help="红方智能体")
    parser.add_argument("--agent2", choices=AGENT_NAMES, default="random", help="黑方智能体")
    parser.add_argument("--games", type=int, default=1, help="对局数")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    args = parser.parse_args()

    agent1 = make_agent(args.agent1)
    agent2 = make_agent(args.agent2)

    results = {Player.red: 0, Player.black: 0, None: 0}
    total_moves = 0
    total_time = 0

    for i in range(args.games):
        if not args.quiet:
            print(f"\n========== 对局 {i+1}/{args.games} ==========")
        winner, moves, duration = play_game(agent1, agent2, verbose=not args.quiet)
        results[winner] += 1
        total_moves += moves
        total_time += duration

    print("\n========== 统计 ==========")
    print(f"对局数: {args.games}")
    print(f"红方 ({args.agent1}) 胜: {results[Player.red]}")
    print(f"黑方 ({args.agent2}) 胜: {results[Player.black]}")
    print(f"未决: {results[None]}")
    print(f"平均步数: {total_moves / args.games:.1f}")
    print(f"平均用时: {total_time / args.games:.2f}s")


if __name__ == "__main__":
    main()
