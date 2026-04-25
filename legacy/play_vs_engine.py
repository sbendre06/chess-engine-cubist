#!/usr/bin/env python3
"""
Play antichess against the Cubist engine in terminal.

Examples:
  .venv/bin/python tools/play_vs_engine.py
  .venv/bin/python tools/play_vs_engine.py --depth 4 --you black
  .venv/bin/python tools/play_vs_engine.py --movetime 500
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import chess

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legacy.antiengine.board import EngineState
from legacy.antiengine.eval import AntichessEvaluator
from legacy.antiengine.search import iterative_deepening
from legacy.antiengine.tt import TranspositionTable
from legacy.antiengine.types import SearchConfig


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Play antichess against Cubist engine.")
    parser.add_argument(
        "--you",
        choices=["white", "black"],
        default="white",
        help="Choose your side.",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Engine fixed search depth (ignored when --movetime is set).",
    )
    parser.add_argument(
        "--movetime",
        type=int,
        default=None,
        help="Engine move time in ms (if set, takes precedence over --depth).",
    )
    parser.add_argument(
        "--hash",
        type=int,
        default=64,
        help="Transposition-table size in MB.",
    )
    return parser.parse_args()


def _print_position(board: chess.Board) -> None:
    print()
    print(board)
    print(f"FEN: {board.fen()}")
    print(f"Side to move: {'White' if board.turn == chess.WHITE else 'Black'}")
    legal = list(board.legal_moves)
    print(f"Legal moves ({len(legal)}): {' '.join(move.uci() for move in legal)}")
    print()


def _human_move(state: EngineState) -> None:
    board = state.board
    while True:
        user_input = input("Your move (UCI, e.g. e2e4): ").strip()
        if user_input in {"quit", "exit"}:
            raise KeyboardInterrupt
        try:
            move = chess.Move.from_uci(user_input)
        except ValueError:
            print("Invalid UCI format.")
            continue
        if move not in board.legal_moves:
            print("Illegal move in this position.")
            continue
        state.push_move(move)
        return


def _engine_move(state: EngineState, config: SearchConfig, tt: TranspositionTable, evaluator: AntichessEvaluator) -> None:
    board = state.copy_board()
    result = iterative_deepening(board, config=config, tt=tt, evaluator=evaluator)
    if result.best_move_uci is None:
        legal = list(state.board.legal_moves)
        if not legal:
            return
        chosen = legal[0]
    else:
        chosen = chess.Move.from_uci(result.best_move_uci)
        if chosen not in state.board.legal_moves:
            chosen = list(state.board.legal_moves)[0]

    state.push_move(chosen)
    print(
        "Engine move:"
        f" {chosen.uci()} (depth={result.depth_completed}, score={result.score_cp},"
        f" nodes={result.nodes}, time_ms={int(result.elapsed_ms)})"
    )


def main() -> None:
    args = _parse_args()
    you_are_white = args.you == "white"

    config = SearchConfig(max_depth=max(1, args.depth))
    if args.movetime is not None and args.movetime > 0:
        config.movetime_ms = args.movetime

    state = EngineState()
    tt = TranspositionTable(megabytes=max(1, args.hash))
    evaluator = AntichessEvaluator()

    print("Cubist AntiChess terminal mode")
    print("Type 'quit' to exit.")

    try:
        while not state.is_game_over():
            board = state.board
            _print_position(board)

            human_turn = (board.turn == chess.WHITE and you_are_white) or (
                board.turn == chess.BLACK and not you_are_white
            )
            if human_turn:
                _human_move(state)
            else:
                _engine_move(state, config, tt, evaluator)
    except KeyboardInterrupt:
        print("\nGoodbye.")
        return

    _print_position(state.board)
    outcome = state.outcome()
    if outcome is None:
        print("Game over.")
        return

    if outcome.winner is None:
        print("Draw.")
        return

    winner = "White" if outcome.winner == chess.WHITE else "Black"
    print(f"Game over. Winner: {winner}")
    print("In antichess, winner is the side that gets rid of all pieces or has no legal moves.")


if __name__ == "__main__":
    main()
