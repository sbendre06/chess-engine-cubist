"""
EngineState: thin, testable wrapper around chess.variant.AntichessBoard.

Responsibilities (Person 1 / rules):
- Own the live position for search and UCI.
- Expose helpers: copy for search, apply UCI move list, reset to startpos / FEN.
- Document antichess invariants for callers:
  - If any capture exists, only captures are legal (python-chess enforces this).
  - Kings are capturable; "check" is not special.
  - Stalemate: side to move has no legal moves -> that side wins (antichess rule).
- Optional: zobrist / transposition_key passthrough for TT.
"""

from __future__ import annotations


class EngineState:
    """
    Wrap AntichessBoard with engine-specific conveniences.

    Methods to implement:
    - __init__: construct from empty, startpos, or FEN.
    - board / inner: access underlying python-chess board if needed by search.
    - push_uci(move_str) -> validate and apply; raise or return error for UCI layer.
    - push_move(move): apply chess.Move.
    - pop(): undo last move for search.
    - reset_startpos / set_fen(fen): UCI position command support.
    - play_moves(moves: list[str]): apply space-separated UCI moves from position cmd.
    - is_game_over() / outcome: detect terminal for search (including stalemate win).
    - transposition_key(): delegate to board for TT hashing.
    """

    ...
