#!/usr/bin/env python3
"""
Engine-vs-engine gauntlet for antichess.

Examples:
  .venv/bin/python tools/match.py --games 100 \
    --engine-a cubist --engine-b "fairy-stockfish"

  .venv/bin/python tools/match.py --games 50 \
    --engine-a cubist --engine-b random --movetime-ms 200
"""

from __future__ import annotations

import argparse
import math
import pathlib
import random
import shlex
import statistics
import sys
import time
from dataclasses import dataclass
from typing import Protocol

import chess
import chess.engine
import chess.pgn
import chess.variant

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legacy.antiengine.board import EngineState
from legacy.antiengine.eval import AntichessEvaluator
from legacy.antiengine.search import iterative_deepening
from legacy.antiengine.tt import TranspositionTable
from legacy.antiengine.types import SearchConfig


@dataclass(slots=True)
class MatchConfig:
    games: int
    movetime_ms: int | None
    depth: int
    hash_mb: int
    pgn_path: str | None
    max_plies: int


@dataclass(slots=True)
class GameResult:
    index: int
    white_name: str
    black_name: str
    winner: str | None
    plies: int
    elapsed_s: float


@dataclass(slots=True)
class MatchReport:
    engine_a_name: str
    engine_b_name: str
    games: int
    engine_a_wins: int
    engine_b_wins: int
    draws: int
    avg_plies: float
    avg_game_seconds: float
    elo_diff_a_minus_b: float | None
    elo_ci95: tuple[float, float] | None


class MoveEngine(Protocol):
    name: str

    def choose_move(self, board: chess.variant.AntichessBoard) -> chess.Move:
        ...

    def close(self) -> None:
        ...


class CubistAdapter:
    def __init__(self, *, depth: int, movetime_ms: int | None, hash_mb: int) -> None:
        self.name = "cubist"
        self._state = EngineState()
        self._tt = TranspositionTable(megabytes=max(1, hash_mb))
        self._evaluator = AntichessEvaluator()
        self._config = SearchConfig(max_depth=max(1, depth))
        if movetime_ms is not None:
            self._config.movetime_ms = max(1, movetime_ms)

    def choose_move(self, board: chess.variant.AntichessBoard) -> chess.Move:
        board_copy = board.copy(stack=True)
        result = iterative_deepening(
            board_copy,
            config=self._config,
            tt=self._tt,
            evaluator=self._evaluator,
        )
        legal = list(board.legal_moves)
        if not legal:
            raise ValueError("No legal moves available for Cubist.")
        if result.best_move_uci is None:
            return legal[0]
        move = chess.Move.from_uci(result.best_move_uci)
        if move not in board.legal_moves:
            return legal[0]
        return move

    def close(self) -> None:
        return


class RandomAdapter:
    def __init__(self) -> None:
        self.name = "random"

    def choose_move(self, board: chess.variant.AntichessBoard) -> chess.Move:
        legal = list(board.legal_moves)
        if not legal:
            raise ValueError("No legal moves available for random adapter.")
        return random.choice(legal)

    def close(self) -> None:
        return


class UciAdapter:
    def __init__(
        self,
        command: str,
        *,
        depth: int,
        movetime_ms: int | None,
        hash_mb: int,
    ) -> None:
        self.name = command
        argv = shlex.split(command)
        if not argv:
            raise ValueError("Empty UCI command.")
        self._engine = chess.engine.SimpleEngine.popen_uci(argv)
        try:
            self._engine.configure({"UCI_Variant": "antichess"})
        except (chess.engine.EngineError, chess.engine.EngineTerminatedError):
            pass
        try:
            self._engine.configure({"Hash": max(1, hash_mb)})
        except (chess.engine.EngineError, chess.engine.EngineTerminatedError):
            pass
        self._depth = max(1, depth)
        self._movetime_ms = movetime_ms

    def choose_move(self, board: chess.variant.AntichessBoard) -> chess.Move:
        limit = (
            chess.engine.Limit(time=max(0.001, self._movetime_ms / 1000.0))
            if self._movetime_ms is not None
            else chess.engine.Limit(depth=self._depth)
        )
        result = self._engine.play(board, limit)
        if result.move is None:
            legal = list(board.legal_moves)
            if not legal:
                raise ValueError("No legal moves available for UCI adapter.")
            return legal[0]
        return result.move

    def close(self) -> None:
        self._engine.quit()


def _build_adapter(spec: str, *, depth: int, movetime_ms: int | None, hash_mb: int) -> MoveEngine:
    normalized = spec.strip().lower()
    if normalized == "cubist":
        return CubistAdapter(depth=depth, movetime_ms=movetime_ms, hash_mb=hash_mb)
    if normalized == "random":
        return RandomAdapter()
    return UciAdapter(spec, depth=depth, movetime_ms=movetime_ms, hash_mb=hash_mb)


def _score_to_elo(score: float) -> float | None:
    if score <= 0.0 or score >= 1.0:
        return None
    return -400.0 * math.log10((1.0 / score) - 1.0)


def _elo_ci95(score: float, games: int) -> tuple[float, float] | None:
    if games <= 0:
        return None
    # Normal approximation over Bernoulli score points (W=1, D=0.5, L=0).
    se = math.sqrt(max(1e-12, score * (1.0 - score)) / games)
    low_p = max(1e-6, score - 1.96 * se)
    high_p = min(1 - 1e-6, score + 1.96 * se)
    low = _score_to_elo(low_p)
    high = _score_to_elo(high_p)
    if low is None or high is None:
        return None
    return (low, high)


def run_match(engine_a_spec: str, engine_b_spec: str, config: MatchConfig) -> MatchReport:
    engine_a = _build_adapter(
        engine_a_spec,
        depth=config.depth,
        movetime_ms=config.movetime_ms,
        hash_mb=config.hash_mb,
    )
    engine_b = _build_adapter(
        engine_b_spec,
        depth=config.depth,
        movetime_ms=config.movetime_ms,
        hash_mb=config.hash_mb,
    )

    game_results: list[GameResult] = []
    pgn_games: list[chess.pgn.Game] = []
    a_wins = 0
    b_wins = 0
    draws = 0

    try:
        for idx in range(1, config.games + 1):
            board = chess.variant.AntichessBoard()
            start = time.perf_counter()
            white_engine = engine_a if idx % 2 == 1 else engine_b
            black_engine = engine_b if idx % 2 == 1 else engine_a

            pgn = chess.pgn.Game()
            pgn.headers["Event"] = "Cubist Antichess Match"
            pgn.headers["Site"] = "local"
            pgn.headers["Variant"] = "Antichess"
            pgn.headers["Round"] = str(idx)
            pgn.headers["White"] = white_engine.name
            pgn.headers["Black"] = black_engine.name
            node = pgn

            plies = 0
            while not board.is_game_over(claim_draw=True) and plies < config.max_plies:
                mover = white_engine if board.turn == chess.WHITE else black_engine
                move = mover.choose_move(board)
                if move not in board.legal_moves:
                    raise ValueError(f"Illegal move from {mover.name}: {move.uci()}")
                board.push(move)
                node = node.add_variation(move)
                plies += 1

            elapsed = time.perf_counter() - start
            outcome = board.outcome(claim_draw=True)
            winner_name: str | None = None
            if outcome is not None and outcome.winner is not None:
                winner_name = white_engine.name if outcome.winner == chess.WHITE else black_engine.name

            if winner_name is None:
                draws += 1
                pgn.headers["Result"] = "1/2-1/2"
            elif winner_name == engine_a.name:
                a_wins += 1
                pgn.headers["Result"] = "1-0" if outcome and outcome.winner == chess.WHITE else "0-1"
            else:
                b_wins += 1
                pgn.headers["Result"] = "1-0" if outcome and outcome.winner == chess.WHITE else "0-1"

            pgn.headers["PlyCount"] = str(plies)
            game_results.append(
                GameResult(
                    index=idx,
                    white_name=white_engine.name,
                    black_name=black_engine.name,
                    winner=winner_name,
                    plies=plies,
                    elapsed_s=elapsed,
                )
            )
            pgn_games.append(pgn)
            print(
                f"Game {idx}/{config.games}: "
                f"winner={winner_name or 'draw'} plies={plies} time={elapsed:.2f}s",
                flush=True,
            )
    finally:
        engine_a.close()
        engine_b.close()

    if config.pgn_path:
        pgn_path = pathlib.Path(config.pgn_path)
        pgn_path.parent.mkdir(parents=True, exist_ok=True)
        with pgn_path.open("w", encoding="utf-8") as fh:
            for game in pgn_games:
                print(game, file=fh, end="\n\n")

    total_games = max(1, config.games)
    score = (a_wins + 0.5 * draws) / total_games
    elo = _score_to_elo(score)
    ci = _elo_ci95(score, total_games)
    return MatchReport(
        engine_a_name=engine_a.name,
        engine_b_name=engine_b.name,
        games=config.games,
        engine_a_wins=a_wins,
        engine_b_wins=b_wins,
        draws=draws,
        avg_plies=statistics.mean(g.plies for g in game_results) if game_results else 0.0,
        avg_game_seconds=statistics.mean(g.elapsed_s for g in game_results) if game_results else 0.0,
        elo_diff_a_minus_b=elo,
        elo_ci95=ci,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run antichess engine-vs-engine match.")
    parser.add_argument("--games", type=int, default=50, help="Number of games.")
    parser.add_argument("--engine-a", type=str, default="cubist", help="Engine A spec (cubist/random/or UCI command).")
    parser.add_argument("--engine-b", type=str, default="random", help="Engine B spec (cubist/random/or UCI command).")
    parser.add_argument("--depth", type=int, default=3, help="Fixed search depth when movetime is unset.")
    parser.add_argument("--movetime-ms", type=int, default=None, help="Per-move time limit in milliseconds.")
    parser.add_argument("--hash", type=int, default=64, help="Hash/TT size in MB.")
    parser.add_argument("--max-plies", type=int, default=600, help="Emergency max plies per game.")
    parser.add_argument("--pgn-out", type=str, default=None, help="Optional PGN output file path.")
    return parser.parse_args()


def main() -> None:
    """CLI: --games, --white, --black, time controls."""
    args = _parse_args()
    config = MatchConfig(
        games=max(1, args.games),
        movetime_ms=max(1, args.movetime_ms) if args.movetime_ms is not None else None,
        depth=max(1, args.depth),
        hash_mb=max(1, args.hash),
        pgn_path=args.pgn_out,
        max_plies=max(20, args.max_plies),
    )
    report = run_match(args.engine_a, args.engine_b, config)

    print()
    print("=== Match Summary ===")
    print(f"Engine A: {report.engine_a_name}")
    print(f"Engine B: {report.engine_b_name}")
    print(f"Games:    {report.games}")
    print(f"A wins:   {report.engine_a_wins}")
    print(f"B wins:   {report.engine_b_wins}")
    print(f"Draws:    {report.draws}")
    print(f"Avg plies/game: {report.avg_plies:.1f}")
    print(f"Avg seconds/game: {report.avg_game_seconds:.2f}")

    if report.elo_diff_a_minus_b is None:
        print("Elo(A-B): undefined (score is 0% or 100%).")
    else:
        print(f"Elo(A-B): {report.elo_diff_a_minus_b:+.1f}")
    if report.elo_ci95 is not None:
        print(f"95% CI:   [{report.elo_ci95[0]:+.1f}, {report.elo_ci95[1]:+.1f}]")


if __name__ == "__main__":
    main()
