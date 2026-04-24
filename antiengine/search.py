"""
Negamax alpha-beta search core with iterative deepening (Person 2).

Features to implement:
- Fail-soft alpha-beta (document vs fail-hard choice).
- Mate / win / loss terminal scores scaled by ply for shortest win preference.
- Node counter; optional split: nodes, qnodes.
- Principal variation extraction (from TT + PV array).
- Iterative deepening: depth 1..N until movetime or stop; keep last completed best move.
- Move ordering:
  - TT best move first
  - Forced captures naturally narrow branch factor
  - MVV-LVA or antichess-specific ordering (sacrifice high value to force opponent takes)
  - History heuristic (from-square, to-square)
  - Killer moves (two slots per ply)
- Quiescence: in antichess extend capture-only chains while captures forced; do not
  evaluate "quiet" when side to move still has unresolved mandatory captures (see eval notes).
- Diagnostics callback or return SearchResult with depth, score, nodes, nps, pv.

Pruning caution (antichess):
- Defer null-move, LMR, futility, razoring until baseline is stable; zugzwang-heavy variant.

Integration:
- Takes EngineState or read-only board + move push/pop stack.
- Uses Evaluator from eval.py (or types.Evaluator protocol).
- Uses TranspositionTable from tt.py.
"""

from __future__ import annotations

from typing import Any


def negamax_root(
    board,
    *,
    depth: int,
    alpha: int,
    beta: int,
    tt,
    evaluator,
    config,
) -> Any:
    """
    Root negamax: iterate legal moves, return best score and best move for this depth.
    """
    ...


def negamax(
    board,
    depth: int,
    alpha: int,
    beta: int,
    ply: int,
    tt,
    evaluator,
    killers,
    history,
    config,
) -> int:
    """Recursive negamax with alpha-beta; updates killers/history side effects."""
    ...


def quiescence(
    board,
    alpha: int,
    beta: int,
    ply: int,
    tt,
    evaluator,
    config,
) -> int:
    """Capture-forced extension until quiet antichess leaf rules."""
    ...


def iterative_deepening(board, *, config, tt, evaluator) -> Any:
    """
    Loop depth 1..max until time/stop; return SearchResult with best completed line.
    """
    ...
