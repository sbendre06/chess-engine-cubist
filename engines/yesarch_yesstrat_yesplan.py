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
    # AntichessBoard.legal_moves already enforces forced-capture rule.
    return list(board.legal_moves)


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    """Score the position from the side-to-move perspective using inverted piece penalties.

    Args:
        board: chess.variant.AntichessBoard — current position; board.turn
            identifies which side is being evaluated.

    Returns:
        int — side-to-move-positive score.  Components: -(own penalty) +
        (opp penalty) per piece type (inverted material), +10 per own legal move
        (mobility bonus: more choices means more control over the sacrifice
        sequence), and +15 per rank of advancement for each own pawn toward
        promotion.

    Antichess:
        PIECE_PENALTIES are inverted from classical values: bishops score highest
        (hardest to lose), kings lowest.  Unlike some engines, mobility is here
        a positive signal: more legal moves means more control over which piece
        gets sacrificed.  Pawn advancement is rewarded because promoted pawns
        (especially to king) are the key endgame tool in antichess theory.
    """
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
    """Reorder moves to place more promising lines first for alpha-beta pruning.

    Args:
        board: chess.variant.AntichessBoard — current position; used to
            classify moves and look up piece penalties and attack state.
        moves: list[chess.Move] — filtered legal moves to reorder.

    Returns:
        list[chess.Move] — same moves sorted by descending priority score.
        Captures score by the penalty of the capturing piece (prefer using
        our most burdensome piece) and by landing on opponent-attacked squares.
        Quiet moves to opponent-attacked squares also score positively.
        Promotions to king score +500; other promotions +200.

    Antichess:
        Captures are scored by the attacker's own penalty, not the classical
        victim value: we want to sacrifice our highest-burden pieces first.
        King promotion (+500) is the top-priority promotion because a promoted
        king is short-ranged and harder for the opponent to avoid capturing,
        making it easier to shed from our inventory.
    """
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
