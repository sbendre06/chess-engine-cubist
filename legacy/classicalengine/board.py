from __future__ import annotations

import chess


class EngineState:
    def __init__(self, fen: str | None = None) -> None:
        self._board = chess.Board()
        if fen is not None:
            self._board.set_fen(fen)

    @property
    def board(self) -> chess.Board:
        return self._board

    def copy_board(self) -> chess.Board:
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
