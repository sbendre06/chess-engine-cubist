#!/usr/bin/env python3
"""
Divide perft for AntichessBoard: legal move counts by depth (Person 4).

Usage sketch:
  python tools/perft.py --depth 4 [--fen ...]

Responsibilities:
- Recursive or split perft counting only legal antichess moves
- Compare to known reference lines at depth 1–4 for regression
- Optional: bulk mode reading positions from data/
"""

from __future__ import annotations


def perft(board, depth: int) -> int:
    """Return node count at `depth` plies from `board`."""
    ...


def main() -> None:
    """CLI wrapper."""
    ...
