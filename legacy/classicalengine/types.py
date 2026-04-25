from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class SearchResult:
    depth_completed: int
    best_move_uci: str | None
    score_cp: int
    pv_uci: list[str]
    nodes: int
    elapsed_ms: float
    nps: int
    stopped: bool = False
    bound: str = "exact"


@dataclass
class SearchConfig:
    max_depth: int = 5
    movetime_ms: int | None = None
    infinite: bool = False
    nodes_limit: int | None = None
    qsearch_max_depth: int = 16


class Evaluator(Protocol):
    def evaluate(self, board, *, ply: int = 0) -> int:
        ...


class TranspositionTableProtocol(Protocol):
    def probe(self, key: int, depth: int):
        ...

    def store(self, key: int, depth: int, score: int, flag, best_move) -> None:
        ...


class UCIEngine(Protocol):
    def handle_command(self, line: str) -> None:
        ...

    @property
    def quit_requested(self) -> bool:
        ...
