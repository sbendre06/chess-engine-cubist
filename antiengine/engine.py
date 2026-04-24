"""
UCIEngine facade: wires EngineState, Search, Eval, TT, optional TB (integrator).

Responsibilities:
- Construct subcomponents from UCI setoption (Hash, SyzygyPath, custom eval weights file).
- Implement types.UCIEngine protocol: handle_command(line) or split parse_uci / dispatch.
- position / go / stop state machine:
  - go: run iterative_deepening in main thread or worker; set abort flag on stop.
- bestmove fallback: if search fails or depth 0, pick random legal move (MVP) then improve.
- Aggregate diagnostics for info string formatting.

Keep this file orchestration-only; no deep alpha-beta here (search.py).
"""

from __future__ import annotations


class UCIEngine:
    """Top-level engine object used by uci.py."""

    def __init__(self) -> None:
        """Create board wrapper, TT, evaluator, search config defaults."""
        ...

    def handle_command(self, line: str) -> None:
        """Parse one UCI line and update state or launch search (types.UCIEngine)."""
        ...

    def go(self, search_config) -> None:
        """Start search from current position; emit info + bestmove when done."""
        ...

    def stop_search(self) -> None:
        """Signal search to finish quickly with best move so far."""
        ...
