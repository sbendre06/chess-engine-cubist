"""Baseline reference antichess engine.

Hand-written, not AI-generated. The yardstick every ablation-branch engine
is scored against. Ported verbatim from the original main.py AI-edit hooks
(get_pseudo_legal_moves, evaluate_board) plus a simple capture-first
order_moves that mirrors the harness's prior built-in ordering.
"""

from __future__ import annotations

import chess
import chess.variant


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 400,
}


def get_pseudo_legal_moves(board: chess.variant.AntichessBoard) -> list[chess.Move]:
    """Return candidate moves, enforcing antichess's forced-capture rule."""
    moves = list(board.pseudo_legal_moves)
    captures = [move for move in moves if board.is_capture(move)]
    return captures if captures else moves


def evaluate_board(board: chess.variant.AntichessBoard) -> int:
    """Antichess heuristic from the side-to-move perspective.

    Material and mobility signs are INVERTED vs classical chess:
      - Fewer own pieces is better (closer to the win condition).
      - Fewer own moves is better (harder to be forced).
      - Capture availability for opponent is good (they must take).
    """
    side = board.turn
    opp = not side

    own_material = 0
    opp_material = 0
    own_pieces = 0
    opp_pieces = 0
    for piece in board.piece_map().values():
        value = PIECE_VALUES[piece.piece_type]
        if piece.color == side:
            own_material += value
            own_pieces += 1
        else:
            opp_material += value
            opp_pieces += 1

    own_moves = get_pseudo_legal_moves(board)
    opp_probe = board.copy(stack=False)
    opp_probe.turn = opp
    opp_moves = get_pseudo_legal_moves(opp_probe)

    own_capture_count = sum(1 for move in own_moves if board.is_capture(move))
    opp_capture_count = sum(1 for move in opp_moves if opp_probe.is_capture(move))

    return (
        150 * (opp_pieces - own_pieces)
        + (opp_material - own_material) // 10
        - 4 * len(own_moves)
        + 4 * len(opp_moves)
        - 12 * own_capture_count
        + 12 * opp_capture_count
    )


def _capture_value(board: chess.variant.AntichessBoard, move: chess.Move) -> int:
    if not board.is_capture(move):
        return 0
    captured = board.piece_at(move.to_square)
    if captured is not None:
        return PIECE_VALUES.get(captured.piece_type, 0)
    if board.is_en_passant(move):
        return PIECE_VALUES[chess.PAWN]
    return 0


def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    """Captures first (biggest victim first), then promotions, then quiets."""
    return sorted(
        moves,
        key=lambda move: (
            1 if board.is_capture(move) else 0,
            1 if move.promotion is not None else 0,
            _capture_value(board, move),
            PIECE_VALUES.get(move.promotion, 0),
        ),
        reverse=True,
    )
