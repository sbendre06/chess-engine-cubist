"""Wrap an engine module with eval noise for stochastic play.

Adds uniform [-noise_cp, +noise_cp] jitter inside evaluate_board so deterministic
engines sample from near-tied moves instead of always picking the first one.
Engines stay untouched; the wrapper is applied at adapter construction time.
"""

from __future__ import annotations

import random
from types import SimpleNamespace
from typing import Any


def wrap_with_eval_noise(
    engine_module: Any,
    noise_cp: int,
    rng: random.Random,
) -> Any:
    """Return a shim exposing the Core 3 callables, with evaluate_board jittered.

    noise_cp <= 0 returns the original module unchanged (zero-cost passthrough).
    The shim is a SimpleNamespace; the harness uses attribute access on the
    engine, so any object exposing the 3 callables works.
    """
    if noise_cp <= 0:
        return engine_module

    base_evaluate = engine_module.evaluate_board
    lo, hi = -noise_cp, noise_cp

    def evaluate_board(board):
        return base_evaluate(board) + rng.randint(lo, hi)

    return SimpleNamespace(
        get_pseudo_legal_moves=engine_module.get_pseudo_legal_moves,
        evaluate_board=evaluate_board,
        order_moves=engine_module.order_moves,
    )
