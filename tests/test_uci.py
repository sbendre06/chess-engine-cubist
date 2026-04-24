"""
Tests for UCI command parsing and engine responses (Person 1).

Cases to cover:
- uci handshake prints required options and uciok
- isready -> readyok
- position startpos moves ... updates internal board correctly
- position fen ... moves ...
- go depth 1 returns legal bestmove for antichess
- stop interrupts long search (may need short movetime test)
"""

from __future__ import annotations


def test_uci_placeholder():
    """Remove when real tests exist; ensures pytest collects module."""
    ...
