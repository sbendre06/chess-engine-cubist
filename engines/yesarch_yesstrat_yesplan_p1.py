from __future__ import annotations

import chess
import chess.variant

# Antichess piece values: having each type is a liability (inverted intent).
# King is cheap (short range, useful as drawing/stalemate tool).
# All others scale by standard mobility to reflect capture-chain danger.
PIECE_VALUES: dict[int, int] = {
    chess.PAWN: 100,
    chess.KNIGHT: 300,
    chess.BISHOP: 300,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 200,
}


def get_pseudo_legal_moves(
    board: chess.variant.AntichessBoard,
) -> list[chess.Move]:
    """Return all legal moves for the current position.

    Args:
        board: chess.variant.AntichessBoard — current position.

    Returns:
        list[chess.Move] — all moves from board.legal_moves, which already
        enforces the forced-capture rule: only captures are returned when any
        capture is available.

    Antichess:
        Delegates to board.legal_moves so the forced-capture rule is handled
        by python-chess internally.  The harness re-filters through
        board.legal_moves regardless, so this is correct and safe.
    """
    # AntichessBoard.legal_moves already enforces mandatory captures:
    # returns captures-only when any capture is available.
    return list(board.legal_moves)


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    """Score the position for the side to move; higher is better for the side to move.

    Args:
        board: chess.variant.AntichessBoard — current position; board.turn
            identifies which side is being evaluated.

    Returns:
        int — side-to-move-positive score.  Components (all via bitboard ops):
        -own_material (inverted material, fewer/cheaper own pieces is better),
        +65 per own piece under opponent attack (capture liability bonus),
        +15 per opponent piece we currently threaten (capture pressure bonus),
        -20 per own piece (raw piece-count penalty), +8 * rank advancement per
        own pawn.  Terminal positions are scored by the harness with MATE_SCORE.

    Antichess:
        All material signs are inverted: own pieces are liabilities.  Capture
        liability (own pieces en prise) is the primary positional tension in
        antichess: an attacked own piece will likely be taken next ply,
        reducing our piece count toward the win condition of zero pieces.
        Pawn advancement is rewarded because advanced pawns can promote and
        are the key endgame tool per Watkins' proof.
    """
    side = board.turn
    them = not side

    own_bb = board.occupied_co[side]
    them_bb = board.occupied_co[them]

    # --- Inverted material: fewer/cheaper own pieces = higher score ---
    own_material = 0
    for sq in chess.scan_forward(own_bb):
        own_material += PIECE_VALUES[board.piece_type_at(sq)]  # type: ignore[index]
    score = -own_material

    # --- Capture Liability (bitboard): own pieces currently under opponent attack.
    # Each such piece is in a forced-capture threat zone → likely captured → good.
    # Watkins: "capture liability" is the key positional tension in antichess.
    opp_attacks: int = 0
    for sq in chess.scan_forward(them_bb):
        opp_attacks |= board.attacks_mask(sq)
    capture_liability = chess.popcount(opp_attacks & own_bb)
    score += capture_liability * 65

    # --- Capture Pressure: how many opponent pieces WE currently attack.
    # More = we have forced-capture choices, letting us select the best sacrifice.
    own_attacks: int = 0
    for sq in chess.scan_forward(own_bb):
        own_attacks |= board.attacks_mask(sq)
    capture_pressure = chess.popcount(own_attacks & them_bb)
    score += capture_pressure * 15

    # --- Piece count penalty: fewer own pieces = closer to win condition ---
    score -= chess.popcount(own_bb) * 20

    # --- Pawn advancement bonus (Watkins: pawn pushes are the endgame key) ---
    own_pawns = board.pawns & own_bb
    for sq in chess.scan_forward(own_pawns):
        rank = chess.square_rank(sq)
        advancement = rank if side == chess.WHITE else (7 - rank)
        score += advancement * 8

    return score


def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    """Reorder moves: chain-reaction captures first, then MVA captures, then promotions.

    Args:
        board: chess.variant.AntichessBoard — current position; used to
            classify moves, look up piece values, and compute the opponent's
            pre-move attack mask.
        moves: list[chess.Move] — filtered legal moves to reorder.

    Returns:
        list[chess.Move] — same moves sorted by descending score_move value.
        Chain-reaction captures (our piece lands on an opponent-attacked square,
        triggering an immediate forced recapture) score +1500 bonus on top of
        the MVA score.  Promotions add 400 + PIECE_VALUES[promotion piece].

    Antichess:
        MVA ordering (Most Valuable Attacker, not victim) means we prefer to
        sacrifice our queen/rook first — shedding high-value pieces is the goal.
        The chain-reaction bonus is the highest-priority signal: if the opponent
        must immediately recapture after our move, two pieces leave the board
        in one move-pair, accelerating our progress toward zero pieces.
        The opponent attack mask is precomputed once per call for efficiency.
    """
    them = not board.turn

    # Precompute opponent attack mask once for all moves in this call.
    them_attacks: int = 0
    for sq in chess.scan_forward(board.occupied_co[them]):
        them_attacks |= board.attacks_mask(sq)

    def score_move(move: chess.Move) -> int:
        s = 0

        if board.is_capture(move):
            attacker_type = board.piece_type_at(move.from_square)
            # MVA: sacrifice our most valuable piece (queen > rook > bishop …)
            s += PIECE_VALUES.get(attacker_type, 0) * 2  # type: ignore[arg-type]

            # Chain-reaction bonus: landing square is currently attacked by opponent.
            # They will be forced to recapture us on the very next ply.
            if chess.BB_SQUARES[move.to_square] & them_attacks:
                s += 1500

        if move.promotion:
            # Promotions are always good: pawn leaves, new piece enters.
            s += 400 + PIECE_VALUES.get(move.promotion, 900)  # type: ignore[arg-type]

        return s

    return sorted(moves, key=score_move, reverse=True)
