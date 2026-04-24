"""
Transposition table for alpha-beta (Person 2).

Design:
- Key: int from board.transposition_key(); if unavailable use stable FEN-based hash (slower).
- Entry fields: depth, score, bound (exact / lower / upper), best_move (optional).
- Replacement policy: depth-preferred or shallow overwrite (document choice).
- Size: configurable buckets; align with UCI Hash option (MB -> entry count estimate).

Functions / classes to implement:
- class TTEntry: dataclass for stored fields.
- class TranspositionTable: probe, store, clear, resize (on setoption hash).
- flag helpers: exact, lower_bound, upper_bound for fail-soft alpha-beta.
"""

from __future__ import annotations


class TranspositionTable:
    """Fixed-size TT; thread-unsafe initially (single search thread)."""

    def probe(self, key: int, depth: int):
        """Return TTEntry or None if miss or unusable (depth/stale rules)."""
        ...

    def store(self, key: int, depth: int, score: int, flag, best_move) -> None:
        """Insert or replace per replacement scheme."""
        ...

    def clear(self) -> None:
        """On ucinewgame and hash resize."""
        ...

    def resize(self, megabytes: int) -> None:
        """Reallocate table from UCI Hash."""
        ...
