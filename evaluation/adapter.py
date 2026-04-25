"""Adapter that presents an engines/<name>.py module as a move-chooser.

Wraps harness.iterative_deepening around a loaded engine module and conforms
to the MoveEngine protocol (name, choose_move, close) used by the match loop.
"""

from __future__ import annotations

import chess
import chess.variant

from harness.engine import SearchConfig, iterative_deepening
from harness.loader import load_engine


class HarnessAdapter:
    def __init__(
        self,
        engine_name: str,
        *,
        depth: int,
        movetime_ms: int | None,
    ) -> None:
        self.name = engine_name
        self._engine_module = load_engine(engine_name)
        self._config = SearchConfig(max_depth=max(1, depth))
        if movetime_ms is not None:
            self._config.movetime_ms = max(1, movetime_ms)

    def choose_move(self, board: chess.variant.AntichessBoard) -> chess.Move:
        board_copy = board.copy(stack=True)
        result = iterative_deepening(board_copy, self._engine_module, self._config)
        legal = list(board.legal_moves)
        if not legal:
            raise ValueError(f"No legal moves available for {self.name}.")
        if result.best_move_uci is None:
            return legal[0]
        move = chess.Move.from_uci(result.best_move_uci)
        if move not in legal:
            return legal[0]
        return move

    def close(self) -> None:
        return
