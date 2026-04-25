"""Generate balanced opening positions for tournament play.

Random plies from the standard antichess start, filtered by a reference
engine's evaluation so neither side is already winning by more than a
threshold. The reference engine acts as the balance oracle; positions where
|score_cp| > balance_threshold_cp are dropped.

Pairing the resulting positions (each played twice with colors swapped) is
done in the match loop, not here. This module only produces FENs.
"""

from __future__ import annotations

import random

import chess
import chess.variant

from harness.engine import SearchConfig, iterative_deepening
from harness.loader import load_engine


def _random_position(plies: int, rng: random.Random) -> chess.variant.AntichessBoard:
    board = chess.variant.AntichessBoard()
    for _ in range(plies):
        if board.is_game_over(claim_draw=True):
            break
        moves = list(board.legal_moves)
        if not moves:
            break
        board.push(rng.choice(moves))
    return board


def generate_balanced_openings(
    count: int,
    *,
    plies: int = 4,
    balance_threshold_cp: int = 200,
    reference_engine: str = "baseline",
    eval_depth: int = 2,
    rng: random.Random | None = None,
    max_attempts_factor: int = 20,
) -> list[str]:
    """Return up to `count` opening FENs filtered to |reference_eval| <= threshold.

    Reference engine evaluates each candidate at `eval_depth`; positions where
    one side is already winning by more than `balance_threshold_cp` (from the
    side-to-move's perspective) are dropped and another candidate is drawn.

    If the attempt budget runs out before `count` positions are found, returns
    however many survived and prints a warning. The caller should treat the
    returned length as authoritative.
    """
    if count <= 0:
        return []

    rng = rng or random.Random()
    reference = load_engine(reference_engine)
    config = SearchConfig(max_depth=max(1, eval_depth))

    fens: list[str] = []
    attempts = 0
    max_attempts = max(count * max_attempts_factor, count + 1)

    while len(fens) < count and attempts < max_attempts:
        attempts += 1
        board = _random_position(plies, rng)
        if board.is_game_over(claim_draw=True):
            continue
        result = iterative_deepening(board.copy(stack=True), reference, config)
        if abs(result.score_cp) > balance_threshold_cp:
            continue
        fens.append(board.fen())

    if len(fens) < count:
        print(
            f"warning: only {len(fens)}/{count} balanced openings found "
            f"after {attempts} attempts (threshold={balance_threshold_cp}cp, "
            f"plies={plies}). Consider raising threshold or lowering plies."
        )
    return fens
