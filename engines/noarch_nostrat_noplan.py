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
    """Return all pseudo-legal moves for the current position.

    Args:
        board: chess.variant.AntichessBoard — current position.

    Returns:
        list[chess.Move] — all moves from board.pseudo_legal_moves, which may
        include quiet moves even when a capture is available.  The harness
        filters this list through board.legal_moves before playing any move,
        discarding quiet moves whenever a capture exists.

    Antichess:
        The forced-capture rule is not enforced here; the harness's legal-move
        filter handles it.  Returning pseudo-legals rather than legals means the
        search sees a superset of legal candidates; none are missed.
    """
    return list(board.pseudo_legal_moves)


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    """Score the position from the side-to-move perspective using inverted piece burden.

    Args:
        board: chess.variant.AntichessBoard — current position; board.turn
            identifies which side is being evaluated.

    Returns:
        int — side-to-move-positive score.  Components: -3 * own_burden
        (inverted material, fewer/cheaper own pieces is better), +opp_burden,
        +2 * attacked_bonus (own pieces under opponent attack will soon be
        captured, reducing our piece count), -10 * own_moves (fewer legal
        moves approaches stalemate, a win in antichess).

    Antichess:
        PIECE_BURDEN reflects how hard each piece type is to sacrifice, not
        classical piece strength.  Stalemate (zero legal moves) is a win for
        the stalemated side, so low own mobility is scored positively.
        Terminal positions are not handled here; the harness scores those
        with MATE_SCORE via _terminal_score.
    """
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
    """Reorder moves to place more promising lines first for alpha-beta pruning.

    Args:
        board: chess.variant.AntichessBoard — current position; used to
            classify moves, look up piece burdens, and detect attacked squares.
        moves: list[chess.Move] — filtered legal moves to reorder.

    Returns:
        list[chess.Move] — same moves sorted by descending priority score.
        Captures score +2000 base, with higher scores for capturing low-burden
        opponent pieces (keeping their heavy pieces as their problem).
        Promotions to low-burden pieces score highly.  Quiet moves to opponent-
        attacked squares score last.

    Antichess:
        Unlike classical chess, low-burden opponent captures are preferred:
        capturing a pawn (burden 500) scores lower than capturing a queen
        (burden 100) because we want the opponent to keep their heavy pieces.
        Moving to attacked squares on quiet moves is rewarded because the piece
        will likely be captured next ply, advancing the win condition.
    """
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
