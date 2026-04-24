"""
python-chess AntichessBoard legality tests (Person 1).

Cases to cover:
- When captures exist, non-capture moves are illegal
- King can be captured; no special check evasion
- Stalemate: side with no legal moves wins (verify outcome / is_checkmate-like APIs)
- Promotion moves including underpromotion to king if supported
"""

from __future__ import annotations


def test_rules_placeholder():
    ...
