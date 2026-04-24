"""
Shared datatypes and protocols for search, evaluation, and UCI.

Integrator owns these contracts so workstreams agree on shapes before implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

# --- Search types ---
#
# SearchResult: depth completed, best move, principal variation, score (centipawns or mate),
#   node count, elapsed time, bound type from TT if applicable.
#
# SearchConfig: max depth, movetime ms, optional nodes limit, hash size MB, threads (future),
#   whether to use TB at leaves, quiescence max depth, etc.


@dataclass
class SearchResult:
    """Outcome of a completed (or interrupted) search."""

    # Fields to add when implementing, e.g.:
    # depth_completed: int
    # best_move_uci: str | None
    # score_cp: int
    # pv_uci: list[str]
    # nodes: int
    # elapsed_ms: float
    # bound: str  # "exact" | "lower" | "upper" if surfacing TT
    pass


@dataclass
class SearchConfig:
    """Parameters controlling iterative deepening, time, and search features."""

    # max_depth, movetime_ms, infinite, hash_mb, syzygy_path, qsearch_max_depth, ...
    pass


# --- Evaluator protocol ---
#
# Evaluator.evaluate(board) -> int from side-to-move perspective, antichess-aware.
# May accept optional SearchConfig / ply for phased eval later.


class Evaluator(Protocol):
    """Pluggable static evaluator (linear weighted features or learned head)."""

    def evaluate(self, board, *, ply: int = 0) -> int:
        ...


# --- Transposition table protocol ---
#
# store(key, depth, score, bound, best_move); probe(key, depth) -> entry or miss
# key: board.transposition_key() preferred; FEN fallback if needed.


class TranspositionTableProtocol(Protocol):
    """TT abstraction so search can be tested with a dict-backed fake."""

    def probe(self, key: int, depth: int):
        ...

    def store(self, key: int, depth: int, score: int, flag, best_move) -> None:
        ...


# --- UCI engine facade ---
#
# UCIEngine: holds board state, search, eval, TT; parses commands; prints UCI info lines.


class UCIEngine(Protocol):
    """High-level object used by uci.py main loop."""

    def handle_command(self, line: str) -> None:
        ...
