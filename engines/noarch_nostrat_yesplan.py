from __future__ import annotations

import chess
import chess.variant

PIECE_VALUE: dict[int, int] = {
    chess.PAWN:   100,
    chess.KNIGHT: 300,
    chess.BISHOP: 300,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   200,
}


def get_pseudo_legal_moves(
    board: chess.variant.AntichessBoard,
) -> list[chess.Move]:
    # AntichessBoard.legal_moves already enforces mandatory captures.
    return list(board.legal_moves)


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    # Goal: lose all own pieces. Fewer own pieces = better (higher score).
    # Bonus for own pieces attacked by opponent: they're about to be captured.
    side = board.turn
    opp = not side
    score = 0
    for pt in chess.PIECE_TYPES:
        val = PIECE_VALUE.get(pt, 0)
        for sq in board.pieces(pt, side):
            score -= val
            if board.is_attacked_by(opp, sq):
                score += val // 2
    return score


def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    # Prefer: captures where our piece lands on an attacked square (chain reaction).
    # Then: other captures. Then: non-captures that expose our pieces. Then: rest.
    def _priority(move: chess.Move) -> int:
        from_piece = board.piece_at(move.from_square)
        if from_piece is None:
            return 0
        from_val = PIECE_VALUE.get(from_piece.piece_type, 0)
        is_cap = board.is_capture(move)

        board.push(move)
        exposed = board.is_attacked_by(board.turn, move.to_square)
        board.pop()

        if is_cap:
            return -(from_val * 2 + (2000 if exposed else 500))
        return -(from_val * 2 if exposed else from_val)

    return sorted(moves, key=_priority)
