"""Shared match loop for head-to-head and tournament runs.

Takes pre-built adapter objects (unlike tools/match.py which builds them from
string specs) so evaluation/ can reuse it across compare.py and tournament.py.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from typing import Protocol

import chess
import chess.variant


class MoveEngine(Protocol):
    name: str
    def choose_move(self, board: chess.variant.AntichessBoard) -> chess.Move: ...
    def close(self) -> None: ...


@dataclass(slots=True)
class MatchConfig:
    games: int = 10
    depth: int = 3
    movetime_ms: int | None = None
    max_plies: int = 600
    openings: list[str] | None = None


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

    @property
    def score_a(self) -> float:
        if self.games <= 0:
            return 0.0
        return (self.engine_a_wins + 0.5 * self.draws) / self.games


def run_match(
    adapter_a: MoveEngine,
    adapter_b: MoveEngine,
    config: MatchConfig,
    *,
    progress: bool = True,
) -> MatchReport:
    """Play config.games games with alternating colors and return aggregate stats."""
    a_wins = b_wins = draws = 0
    plies_record: list[int] = []
    secs_record: list[float] = []

    openings = config.openings or []
    try:
        for idx in range(1, config.games + 1):
            # Pair games (1,2), (3,4), ... so each opening is played twice
            # with colors swapped — bias from the position cancels out.
            board = chess.variant.AntichessBoard()
            if openings:
                board.set_fen(openings[((idx - 1) // 2) % len(openings)])
            white = adapter_a if idx % 2 == 1 else adapter_b
            black = adapter_b if idx % 2 == 1 else adapter_a

            start = time.perf_counter()
            plies = 0
            while not board.is_game_over(claim_draw=True) and plies < config.max_plies:
                mover = white if board.turn == chess.WHITE else black
                move = mover.choose_move(board)
                if move not in board.legal_moves:
                    raise ValueError(f"Illegal move from {mover.name}: {move.uci()}")
                board.push(move)
                plies += 1

            elapsed = time.perf_counter() - start
            outcome = board.outcome(claim_draw=True)
            winner_name = None
            if outcome is not None and outcome.winner is not None:
                winner_name = white.name if outcome.winner == chess.WHITE else black.name

            if winner_name is None:
                draws += 1
            elif winner_name == adapter_a.name:
                a_wins += 1
            else:
                b_wins += 1

            plies_record.append(plies)
            secs_record.append(elapsed)
            if progress:
                print(
                    f"  game {idx}/{config.games}: "
                    f"winner={winner_name or 'draw':<20} plies={plies} time={elapsed:.2f}s",
                    flush=True,
                )
    finally:
        adapter_a.close()
        adapter_b.close()

    return MatchReport(
        engine_a_name=adapter_a.name,
        engine_b_name=adapter_b.name,
        games=config.games,
        engine_a_wins=a_wins,
        engine_b_wins=b_wins,
        draws=draws,
        avg_plies=statistics.mean(plies_record) if plies_record else 0.0,
        avg_game_seconds=statistics.mean(secs_record) if secs_record else 0.0,
    )
