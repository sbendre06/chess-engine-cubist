from __future__ import annotations

from dataclasses import dataclass

EXACT = "exact"
LOWER_BOUND = "lower"
UPPER_BOUND = "upper"


@dataclass(slots=True)
class TTEntry:
    key: int
    depth: int
    score: int
    flag: str
    best_move_uci: str | None


class TranspositionTable:
    def __init__(self, megabytes: int = 64) -> None:
        self._table: list[TTEntry | None] = []
        self._size = 0
        self.resize(megabytes)

    def _index(self, key: int) -> int:
        return key % self._size

    def probe_exact_key(self, key: int) -> TTEntry | None:
        entry = self._table[self._index(key)]
        if entry is not None and entry.key == key:
            return entry
        return None

    def probe(self, key: int, depth: int):
        entry = self.probe_exact_key(key)
        if entry is None or entry.depth < depth:
            return None
        return entry

    def store(self, key: int, depth: int, score: int, flag, best_move) -> None:
        idx = self._index(key)
        best_move_uci = best_move.uci() if best_move is not None else None
        incoming = TTEntry(
            key=key,
            depth=depth,
            score=score,
            flag=flag,
            best_move_uci=best_move_uci,
        )
        existing = self._table[idx]
        if existing is None or existing.key == key or depth >= existing.depth:
            self._table[idx] = incoming

    def clear(self) -> None:
        self._table = [None] * self._size

    def resize(self, megabytes: int) -> None:
        bytes_budget = max(1, megabytes) * 1024 * 1024
        self._size = max(1 << 15, bytes_budget // 32)
        self._table = [None] * self._size
