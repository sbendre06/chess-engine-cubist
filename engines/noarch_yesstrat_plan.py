"""Antichess engine: noarch_yesstrat_plan (condition 0110).

Strategy-aware heuristics for antichess:
- Fewer own pieces is better (goal: lose them all).
- Prefer using high-value pieces to capture (lose queens/rooks first).
- Bonus for positions with more available captures (faster piece reduction).
"""

from __future__ import annotations

import chess
import chess.variant

_PIECE_VALUES: dict[int, int] = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 10,
}


def get_pseudo_legal_moves(
    board: chess.variant.AntichessBoard,
) -> list[chess.Move]:
    """Return all pseudo-legal moves; the harness filters to board.legal_moves."""
    return list(board.pseudo_legal_moves)


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    """Score from side-to-move perspective (higher = better for side to move).

    Core insight for antichess: we want to shed all our pieces as fast as
    possible, so fewer own pieces and more opponent pieces is better.
    """
    my_count = chess.popcount(board.occupied_co[board.turn])
    opp_count = chess.popcount(board.occupied_co[not board.turn])

    # Primary term: piece-count delta (opponent has more pieces = they're
    # further from winning; we have fewer = we're closer to winning).
    piece_score = (opp_count - my_count) * 100

    # Secondary term: bonus per available capture.  Having captures available
    # means we can immediately reduce our piece count this turn.
    capture_bonus = sum(
        10 for m in board.legal_moves if board.is_capture(m)
    )

    return piece_score + capture_bonus


def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    """Order moves: captures first (mandatory when any exist), then non-captures.

    Among captures: prefer moving high-value pieces (we want to lose them).
    Among non-captures: prefer advancing pawns (push them toward the opponent
    so they become capturable sooner).
    """

    def _score(move: chess.Move) -> tuple[int, int]:
        if board.is_capture(move):
            attacker_type = board.piece_type_at(move.from_square)
            attacker_val = _PIECE_VALUES.get(attacker_type, 0) if attacker_type else 0
            # Higher attacker value → we sacrifice a powerful piece → good.
            return (1, attacker_val)

        # Non-capture: rank by how far a pawn advances (closer to promotion =
        # easier to force the opponent to capture it).
        moving_piece = board.piece_type_at(move.from_square)
        if moving_piece == chess.PAWN:
            # White pushes toward rank 8 (high to_square rank); black toward rank 1.
            rank = chess.square_rank(move.to_square)
            advance = rank if board.turn == chess.WHITE else (7 - rank)
            return (0, advance)

        return (0, 0)

    return sorted(moves, key=_score, reverse=True)
