from __future__ import annotations

import chess
import chess.variant

# In Antichess the goal is to LOSE all your pieces or be stalemated.
# Each piece is a "burden" — harder to sacrifice = higher burden value.
# Pawns: very sticky (only captured diagonally, can promote).
# Queens: easiest to sacrifice (attack everywhere, trivial to put in harm's way).
PIECE_BURDEN = {
    chess.PAWN: 500,
    chess.KNIGHT: 300,
    chess.BISHOP: 300,
    chess.ROOK: 150,
    chess.QUEEN: 100,
    chess.KING: 200,
}


def get_pseudo_legal_moves(
    board: chess.variant.AntichessBoard,
) -> list[chess.Move]:
    return list(board.pseudo_legal_moves)


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    side = board.turn
    opp = not side

    own_burden = 0
    opp_burden = 0
    attacked_bonus = 0

    for sq, piece in board.piece_map().items():
        b = PIECE_BURDEN[piece.piece_type]
        if piece.color == side:
            own_burden += b
            # Own pieces under attack will be captured next — good for us.
            if board.is_attacked_by(opp, sq):
                attacked_bonus += b
        else:
            opp_burden += b

    # Count own legal moves: fewer = closer to stalemate (a win in Antichess).
    own_moves = sum(1 for _ in board.legal_moves)

    return (
        -own_burden * 3        # Primary: shed your own pieces
        + opp_burden           # Secondary: opponent burdened with their pieces
        + attacked_bonus * 2   # Pieces about to be captured are great
        - own_moves * 10       # Low mobility → closer to stalemate win
    )


def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    opp = not board.turn

    def priority(move: chess.Move) -> int:
        score = 0

        if board.is_capture(move):
            score += 2000
            target = board.piece_at(move.to_square)
            if target:
                # Prefer capturing low-burden pieces first:
                # opponent keeps high-burden pieces as their own problem.
                score += 600 - PIECE_BURDEN[target.piece_type]
            elif board.is_en_passant(move):
                score += 600 - PIECE_BURDEN[chess.PAWN]

        # Promotions: prefer pieces that are easy to sacrifice (queen/king).
        if move.promotion:
            promo_burden = PIECE_BURDEN.get(move.promotion, 300)
            score += 500 + (600 - promo_burden)

        # Moving into a square already attacked by opponent: good (we get taken).
        moving = board.piece_at(move.from_square)
        if moving and board.is_attacked_by(opp, move.to_square):
            score += PIECE_BURDEN[moving.piece_type] // 2

        return score

    return sorted(moves, key=priority, reverse=True)
