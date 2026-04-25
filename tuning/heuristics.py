"""
Library of scalar feature functions for antichess evaluation (Person 3).

Each feature should be pure: (board, *, color perspective) -> float or int.

Examples to implement (names illustrative):
- material_diff_antichess_perspective
- piece_count_diff
- own_legal_moves_count / opponent_legal_moves_count
- own_forced_captures_count / opponent_forced_captures_count
- capturable_hanging_value (heuristic)
- promotion_distance_min / king_promotion_flag
- stalemate_pressure_proxy (low mobility + low material for side to move)

Export a registry dict[str, Callable] for the optimizer to index by weight name.
"""

from __future__ import annotations


def feature_registry():
    """Return mapping name -> callable for tuning harness."""
    ...
