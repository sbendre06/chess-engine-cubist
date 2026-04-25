"""
Evaluation unit tests (Person 3).

Cases to cover:
- Fewer pieces scores better for side to move when other terms equal (sanity)
- Stalemate-like low mobility bonuses in crafted positions
- Sacrifice heuristic: position where hanging a queen is locally correct scores higher
- Symmetry: flipping colors negates or mirrors score per convention
"""

from __future__ import annotations


def test_eval_placeholder():
    ...