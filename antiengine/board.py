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

import chess
import chess.variant

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

    def __init__(self, fen: str | None = None) -> None:
        self._board = chess.variant.AntichessBoard()
        if fen is not None:
            self._board.set_fen(fen)

    @property
    def board(self) -> chess.variant.AntichessBoard:
        return self._board

    def copy_board(self) -> chess.variant.AntichessBoard:
        return self._board.copy(stack=True)

    def push_uci(self, move_str: str) -> chess.Move:
        move = chess.Move.from_uci(move_str)
        if move not in self._board.legal_moves:
            raise ValueError(f"Illegal move in position: {move_str}")
        self._board.push(move)
        return move

    def push_move(self, move: chess.Move) -> None:
        if move not in self._board.legal_moves:
            raise ValueError(f"Illegal move in position: {move.uci()}")
        self._board.push(move)

    def pop(self) -> chess.Move:
        return self._board.pop()

    def reset_startpos(self) -> None:
        self._board.reset()

    def set_fen(self, fen: str) -> None:
        self._board.set_fen(fen)

    def play_moves(self, moves: list[str]) -> None:
        for move_uci in moves:
            self.push_uci(move_uci)

    def is_game_over(self) -> bool:
        return self._board.is_game_over(claim_draw=True)

    def outcome(self) -> chess.Outcome | None:
        return self._board.outcome(claim_draw=True)

    def transposition_key(self) -> int:
        if hasattr(self._board, "_transposition_key"):
            return hash(self._board._transposition_key())
        return hash(self._board.fen())
