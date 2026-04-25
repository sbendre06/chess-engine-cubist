# AGENT: copy this file to engines/<yourname>.py and replace the bodies below.
# Do NOT edit this template in place. Do NOT import anything from engines/.
"""Starter scaffold for an ablation-branch engine.

You must export exactly three callables with these signatures. The frozen
harness in harness/engine.py will call them; anything outside these three
is not your surface.

Antichess rules you are responsible for encoding:
  - If any capture is legal, only captures may be played (forced-capture rule).
  - Stalemate is a WIN for the side with no legal moves.
  - A side with zero pieces WINS.
  - Material and mobility signs are INVERTED vs classical chess: fewer own
    pieces is better, fewer own moves is better.

The trivial bodies below are enough for `python main.py --engine _template`
to run without crashing, but they play very weak chess. Replace them.
"""

from __future__ import annotations

import chess
import chess.variant


def get_pseudo_legal_moves(board: chess.variant.AntichessBoard) -> list[chess.Move]:
    """Return candidate moves. MUST enforce antichess's forced-capture rule:
    if any pseudo-legal capture exists, only captures may be returned.
    Returned moves need not all be fully legal; the harness filters through
    board.legal_moves before playing anything.
    """
    moves = list(board.pseudo_legal_moves)
    captures = [m for m in moves if board.is_capture(m)]
    return captures if captures else moves


def evaluate_board(board: chess.variant.AntichessBoard) -> int:
    """Static heuristic score in centipawns, from the side-to-move perspective.
    Higher = better for whoever is to move. Called at leaf nodes of search.
    """
    return 0


def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    """Reorder `moves` best-first so alpha-beta gets early cutoffs. Must
    return the same set of moves, just reordered - no additions, no drops.
    """
    return list(moves)
