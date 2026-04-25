# AGENT: copy this file to engines/<yourname>.py and implement the three
# functions below. Do not edit this template in place.

from __future__ import annotations

import chess
import chess.variant


def get_pseudo_legal_moves(
    board: chess.variant.AntichessBoard,
) -> list[chess.Move]:
    raise NotImplementedError


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    raise NotImplementedError


def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    raise NotImplementedError
