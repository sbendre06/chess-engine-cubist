"""
Weight search: grid, random search, genetic algorithm, or SPSA (Person 3).

Responsibilities:
- Load bounds per weight (min/max) from config JSON or constants.
- Call tuning/objective.evaluate_fitness each iteration.
- Log iteration -> weights -> fitness to tuning/params_history/ (JSON lines).
- Optional: early stop on plateau; reproducible RNG seed.

Classes / functions:
- class OptimizationConfig: method, population, generations, mutation rate, etc.
- def run_optimization(config) -> best_weights
"""

from __future__ import annotations


def run_optimization(config) -> dict:
    """Entry point used by tools/tune_eval.py."""
    ...
