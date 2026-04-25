from __future__ import annotations

import chess

from classicalengine.constants import PIECE_VALUE, PST_BY_PIECE


class ClassicalEvaluator:
    """Classical chess evaluator with material + PST + mobility."""

    def _piece_square_score(self, piece_type: int, color: chess.Color, square: chess.Square) -> int:
        table = PST_BY_PIECE[piece_type]
        idx = square if color == chess.WHITE else chess.square_mirror(square)
        return table[idx]

    def evaluate(self, board: chess.Board, *, ply: int = 0) -> int:
        material_white = 0
        material_black = 0
        pst_white = 0
        pst_black = 0

        for square, piece in board.piece_map().items():
            value = PIECE_VALUE[piece.piece_type]
            pst = self._piece_square_score(piece.piece_type, piece.color, square)
            if piece.color == chess.WHITE:
                material_white += value
                pst_white += pst
            else:
                material_black += value
                pst_black += pst

        # Mobility as a lightweight dynamic term.
        own_mobility = board.legal_moves.count()
        probe = board.copy(stack=False)
        probe.turn = not board.turn
        opp_mobility = probe.legal_moves.count()
        mobility_term = 4 * (own_mobility - opp_mobility)

        # White-positive base score.
        white_score = (material_white - material_black) + (pst_white - pst_black)
        score_from_side_to_move = white_score if board.turn == chess.WHITE else -white_score
        return int(score_from_side_to_move + mobility_term)
