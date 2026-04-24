#!/usr/bin/env python3
"""
Engine-vs-engine or engine-vs-random harness (Person 4).

Features to implement:
- Spawn two UCI subprocesses or in-process engines
- Protocol: alternating moves until terminal; log PGN with antichess headers
- Openings: from startpos or EPD shuffle
- Metrics: win rate, illegal move detection, average depth/time per side
- Optional: Fairy-Stockfish as external opponent (binary path), no code copying

Functions:
- run_match(engine_a_cmd, engine_b_cmd, games: int) -> MatchReport
"""

from __future__ import annotations


def main() -> None:
    """CLI: --games, --white, --black, time controls."""
    ...
