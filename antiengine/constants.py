"""
Named constants and default tuned weights (Person 3 + integrator).

Contents to define:
- Piece values for ordering only (not same as eval sign); king/chameleon rules for antichess.
- Mate score base and mate distance ply offset (search.py uses these).
- DRAW / UNKNOWN if ever needed (antichess has fewer draws).
- Default EvalWeights dataclass mirroring features in eval.py / tuning/heuristics.py
- Version string for UCI id name.

No magic numbers scattered: centralize here after first implementation pass.
"""

from __future__ import annotations

from dataclasses import dataclass

ENGINE_NAME = "Cubist AntiChess"
ENGINE_AUTHOR = "Cubist Hackathon Team"
ENGINE_VERSION = "0.1.0"

MATE_VALUE = 100_000
DRAW_VALUE = 0
INFINITY = 1_000_000

# Ordering-centric values (not classical chess eval values).
PIECE_ORDER_VALUE = {
    "P": 100,
    "N": 300,
    "B": 320,
    "R": 500,
    "Q": 900,
    "K": 1_200,
}


@dataclass(frozen=True)
class EvalWeights:
    material_delta: int = 12
    piece_count_delta: int = 20
    own_legal_moves: int = -2
    opp_legal_moves: int = 2
    own_capture_moves: int = -4
    opp_capture_moves: int = 4


DEFAULT_EVAL_WEIGHTS = EvalWeights()
