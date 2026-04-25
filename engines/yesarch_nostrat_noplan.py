from __future__ import annotations

import chess
import chess.variant

# In Antichess, holding pieces is bad — this table encodes how costly each
# piece type is to have. Higher = harder to shed, worse for us.
PIECE_COST = {
    chess.PAWN: 100,
    chess.KNIGHT: 300,
    chess.BISHOP: 350,   # color-locked, notoriously hard to lose
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 200,
}

_MOBILITY_WEIGHT = 10   # penalty per legal move we have (fewer = more constrained = better)
_EXPOSURE_WEIGHT = 4    # bonus per piece of ours that is attacked (it will be captured = good)


def get_pseudo_legal_moves(
    board: chess.variant.AntichessBoard,
) -> list[chess.Move]:
    return list(board.pseudo_legal_moves)


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    if board.is_game_over(claim_draw=True):
        outcome = board.outcome(claim_draw=True)
        if outcome is None or outcome.winner is None:
            return 0
        return 900_000 if outcome.winner == board.turn else -900_000

    me = board.turn
    opp = not me

    # Material: minimize our own holdings, let opponent keep theirs
    my_cost = sum(PIECE_COST[pt] * len(board.pieces(pt, me)) for pt in chess.PIECE_TYPES)
    opp_cost = sum(PIECE_COST[pt] * len(board.pieces(pt, opp)) for pt in chess.PIECE_TYPES)
    score = opp_cost - my_cost

    # Mobility: fewer options = opponent can force captures on us = good
    score -= len(list(board.legal_moves)) * _MOBILITY_WEIGHT

    # Exposure: pieces of ours currently attacked will be captured next turn
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p and p.color == me and board.is_attacked_by(opp, sq):
            score += PIECE_COST[p.piece_type] * _EXPOSURE_WEIGHT

    return score


def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    opp = not board.turn

    def score(move: chess.Move) -> int:
        attacker = board.piece_at(move.from_square)
        att_val = PIECE_COST.get(attacker.piece_type, 0) if attacker else 0

        if board.is_capture(move):
            if board.is_en_passant(move):
                vic_val = PIECE_COST[chess.PAWN]
            else:
                victim = board.piece_at(move.to_square)
                vic_val = PIECE_COST.get(victim.piece_type, 0) if victim else 0

            # Prefer high-value attackers: using our queen/rook to capture means
            # we sacrifice them and initiate a chain if the square is re-attacked.
            chain_bonus = att_val // 2 if board.is_attacked_by(opp, move.to_square) else 0

            return 10_000 + att_val + chain_bonus + vic_val // 4

        # No captures available — prefer moving our pieces onto squares the
        # opponent attacks so they're likely to be captured next.
        if board.is_attacked_by(opp, move.to_square):
            return 5_000 + att_val
        return att_val

    return sorted(moves, key=score, reverse=True)
