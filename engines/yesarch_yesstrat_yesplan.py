from __future__ import annotations

import chess
import chess.variant

# Inverted piece values: owning these pieces is a liability in Antichess.
# Bishops are worst (forced into long capture chains); Kings are safest.
PIECE_PENALTIES = {
    chess.PAWN: 100,
    chess.KNIGHT: 220,
    chess.BISHOP: 400,
    chess.ROOK: 280,
    chess.QUEEN: 160,
    chess.KING: 70,
}


def get_pseudo_legal_moves(
    board: chess.variant.AntichessBoard,
) -> list[chess.Move]:
    # AntichessBoard.legal_moves already enforces forced-capture rule.
    return list(board.legal_moves)


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    side = board.turn
    opp = not side
    score = 0

    # Material: penalise own pieces (liabilities), reward opponent's.
    for pt in chess.PIECE_TYPES:
        penalty = PIECE_PENALTIES[pt]
        score -= len(board.pieces(pt, side)) * penalty
        score += len(board.pieces(pt, opp)) * penalty

    # Mobility: more legal moves = more control over which piece to sacrifice.
    score += len(list(board.legal_moves)) * 10

    # Pawn advancement: advanced pawns can promote to King (hard to capture).
    for sq in board.pieces(chess.PAWN, side):
        rank = chess.square_rank(sq)
        advance = rank if side == chess.WHITE else (7 - rank)
        score += advance * 15

    return score


def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    side = board.turn
    opp = not side

    def move_score(move: chess.Move) -> int:
        score = 0
        pt = board.piece_type_at(move.from_square)
        penalty = PIECE_PENALTIES.get(pt, 0) if pt else 0

        # Prefer capturing with our most burdensome pieces first.
        if board.is_capture(move):
            score += penalty

        # Moving to a square the opponent attacks: likely to be captured = good.
        if board.is_attacked_by(opp, move.to_square):
            score += penalty // 2

        # King promotion is the ideal end-state; other promotions are fine too.
        if move.promotion == chess.KING:
            score += 500
        elif move.promotion:
            score += 200

        # Advance pawns toward promotion.
        if pt == chess.PAWN:
            rank_to = chess.square_rank(move.to_square)
            advance = rank_to if side == chess.WHITE else (7 - rank_to)
            score += advance * 10

        return score

    return sorted(moves, key=move_score, reverse=True)
