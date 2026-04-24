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

# Example placeholders (replace with real constants when implementing):
# MATE_VALUE = ...
# DEFAULT_EVAL_WEIGHTS = ...
