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
    """Return all pseudo-legal moves for the current position.

    Args:
        board: chess.variant.AntichessBoard — current position.

    Returns:
        list[chess.Move] — all moves from board.pseudo_legal_moves, which may
        include quiet moves even when a capture is available.  The harness
        filters this list through board.legal_moves before playing any move,
        enforcing the mandatory-capture rule.

    Antichess:
        The forced-capture rule is not enforced here; the harness handles it.
        Returning pseudo-legals rather than legals guarantees no legal move is
        omitted from the search frontier.
    """
    return list(board.pseudo_legal_moves)


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    """Score the position from the side-to-move perspective using inverted piece cost.

    Args:
        board: chess.variant.AntichessBoard — current position; board.turn
            identifies which side is being evaluated.

    Returns:
        int — side-to-move-positive score.  If the game is over, returns
        ±900_000 (win/loss sentinel).  Otherwise: opp_cost - my_cost (inverted
        material), minus a mobility penalty (_MOBILITY_WEIGHT per legal move),
        plus an exposure bonus (_EXPOSURE_WEIGHT * PIECE_COST for each own piece
        currently attacked by the opponent).

    Antichess:
        PIECE_COST reflects how hard each piece is to shed, not classical
        strength.  Mobility is penalised: fewer own options means the opponent
        can more easily force us into captures, and stalemate (zero moves) is a
        win.  Attacked own pieces score positively because they will be taken,
        reducing our piece count.
    """
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
    """Reorder moves to place more promising lines first for alpha-beta pruning.

    Args:
        board: chess.variant.AntichessBoard — current position; used to
            classify moves, look up piece costs, and detect attacked squares.
        moves: list[chess.Move] — filtered legal moves to reorder.

    Returns:
        list[chess.Move] — same moves sorted by descending score.  Captures
        score 10_000+ (prefer using our high-cost pieces as the attacker, with
        a chain bonus when our piece is immediately recapturable after the
        capture).  Quiet moves to opponent-attacked squares score 5_000+.
        Other quiet moves score by attacker piece cost only.

    Antichess:
        The attacker's piece cost drives capture ordering: using our most
        expensive (hardest-to-lose) piece to capture means we shed it and may
        trigger a recapture chain, removing multiple pieces from our inventory.
        Quiet moves that place our pieces on attacked squares are rewarded
        because the opponent will be forced to take them next ply.
    """
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
