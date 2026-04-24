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


class AntichessEvaluator:
    """Linear (or later non-linear) weighted feature evaluator."""

    def __init__(self, weights=None) -> None:
        """Load default weights from constants.py or passed tuning vector."""
        ...

    def evaluate(self, board, *, ply: int = 0) -> int:
        """Return score from current side to move perspective."""
        ...
