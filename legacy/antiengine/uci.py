"""
UCI protocol loop for Anti-Chess (variant antichess).

CLI: python -m antiengine.uci

Commands to support (Person 1):
- uci / uciok, id name, id author, option definitions, uciok
- isready -> readyok
- ucinewgame
- position startpos [moves ...]
- position fen ... [moves ...]
- go depth N | go movetime T | go infinite (optional) + stop
- quit

Options (minimum):
- UCI_Variant combo default antichess var antichess
- Hash spin default 64 min 1 max 4096
- Optional: SyzygyPath string

Implementation notes:
- Read stdin line-by-line in a loop; dispatch to UCIEngine / EngineState / Search.
- On go: spawn or run search; respect stop flag; always emit bestmove (legal fallback).
- Emit info lines: depth, score, nodes, nps, pv, time, optional tbhits.
"""

from __future__ import annotations

import sys

from legacy.antiengine.engine import UCIEngine


def main() -> None:
    """
    Entry point when run as __main__:
    - Parse or delegate options from uci command into SearchConfig / TB path.
    - Construct UCIEngine (see engine.py) with board, search, eval, TT.
    - Run stdin loop until quit.
    """
    engine = UCIEngine()
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        engine.handle_command(line)
        if engine.quit_requested:
            break


if __name__ == "__main__":
    main()
