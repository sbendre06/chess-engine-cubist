"""
Fitness / loss for a weight vector / genome (Person 3 + Person 4 metrics).

Ideas to implement:
- Load test suite EPD/FEN: engine move vs reference best (puzzle hit rate).
- Self-play or vs baseline engine at shallow depth; Elo-like or win rate.
- Combine: accuracy on tactics + penalty for eval instability + speed budget.

Functions:
- score_weights(engine_factory, weights, suite_path) -> float (higher better or define sign)
- compare_move(chosen_uci, ref_uci) -> bool or partial credit
"""

from __future__ import annotations


def evaluate_fitness(weights, *, suite_path: str, config) -> float:
    """Run suite / matches; return scalar fitness for optimizer."""
    ...
