"""
Static evaluation for Anti-Chess (Person 3).

Normal chess eval is misleading: fewer pieces and lower mobility are often good; stalemate
is a win for the stalemated side; material sign is inverted vs classical chess in spirit.

Baseline linear model (tune weights):
  score ≈ w1 * (opp_material - own_material)
        + w2 * (opp_piece_count - own_piece_count)
        + w3 * own_legal_moves (negative weight)
        + w4 * opp_legal_moves
        + w5 * own_forced_capture_moves (negative)
        + w6 * opp_forced_capture_moves

Feature functions to expose (for tests and tuning/heuristics.py may re-export):
- material_delta / piece_count_by_color
- legal_move_counts; legal_capture_counts
- forced_capture_exists; number of forced capture sequences (approx)
- hanging_own_material; opponent_capture_burden
- promotion_distance / underpromotion signals (king promotions)
- mobility danger: branching that opens non-forced choice for opponent (heuristic)

Evaluator class:
- __init__(weights: dict or EvalWeights dataclass)
- evaluate(board, *, ply) -> int centipawn-ish from side to move

Important:
- Do not return a "quiet" static score when side to move has only captures (all moves captures):
  search/quiescence should extend; eval can assert or delegate to quiescence helper.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass

import chess

from legacy.antiengine.constants import DEFAULT_EVAL_WEIGHTS, PIECE_ORDER_VALUE


def _material_for_color(board: chess.Board, color: chess.Color) -> int:
    total = 0
    for piece in board.piece_map().values():
        if piece.color == color:
            total += PIECE_ORDER_VALUE[piece.symbol().upper()]
    return total


def _piece_count_for_color(board: chess.Board, color: chess.Color) -> int:
    return sum(1 for piece in board.piece_map().values() if piece.color == color)


def _legal_move_count_for_color(board: chess.Board, color: chess.Color) -> int:
    probe = board.copy(stack=False)
    probe.turn = color
    return probe.legal_moves.count()


def _capture_move_count_for_color(board: chess.Board, color: chess.Color) -> int:
    probe = board.copy(stack=False)
    probe.turn = color
    return sum(1 for move in probe.legal_moves if probe.is_capture(move))


class AntichessEvaluator:
    """Linear (or later non-linear) weighted feature evaluator."""

    def __init__(self, weights=None) -> None:
        """Load default weights from constants.py or passed tuning vector."""
        if weights is None:
            self._weights = asdict(DEFAULT_EVAL_WEIGHTS)
        elif is_dataclass(weights):
            self._weights = asdict(weights)
        else:
            self._weights = dict(weights)

    def evaluate(self, board, *, ply: int = 0) -> int:
        """Return score from current side to move perspective."""
        side = board.turn
        opp = not side

        own_material = _material_for_color(board, side)
        opp_material = _material_for_color(board, opp)
        own_pieces = _piece_count_for_color(board, side)
        opp_pieces = _piece_count_for_color(board, opp)

        own_legal = _legal_move_count_for_color(board, side)
        opp_legal = _legal_move_count_for_color(board, opp)
        own_captures = _capture_move_count_for_color(board, side)
        opp_captures = _capture_move_count_for_color(board, opp)

        score = 0
        score += self._weights["material_delta"] * (opp_material - own_material)
        score += self._weights["piece_count_delta"] * (opp_pieces - own_pieces)
        score += self._weights["own_legal_moves"] * own_legal
        score += self._weights["opp_legal_moves"] * opp_legal
        score += self._weights["own_capture_moves"] * own_captures
        score += self._weights["opp_capture_moves"] * opp_captures
        return int(score)
