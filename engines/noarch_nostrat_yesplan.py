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
    """Return all legal moves for the current position.

    Args:
        board: chess.variant.AntichessBoard — current position.

    Returns:
        list[chess.Move] — all moves from board.legal_moves, which already
        enforces the forced-capture rule: only captures are returned when any
        capture is available.

    Antichess:
        Delegates directly to board.legal_moves so the forced-capture rule is
        handled by python-chess internally.  The harness re-filters through
        board.legal_moves regardless, so this is both correct and redundantly safe.
    """
    # AntichessBoard.legal_moves already enforces mandatory captures.
    return list(board.legal_moves)


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    """Score the position from the side-to-move perspective using inverted material.

    Args:
        board: chess.variant.AntichessBoard — current position; board.turn
            identifies which side is being evaluated.

    Returns:
        int — side-to-move-positive score.  For each own piece, subtracts its
        PIECE_VALUE; if that piece is currently attacked by the opponent, adds
        back half its value as a capture-threat bonus (the piece is about to be
        removed from our inventory, which is good).

    Antichess:
        Material signs are fully inverted: owning a piece is a liability.
        The capture-threat bonus reflects that an attacked piece will soon be
        taken, advancing us toward the win condition (zero own pieces).
        Terminal positions are not handled here; the harness scores those
        with MATE_SCORE via _terminal_score.
    """
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
    """Reorder moves to place high-priority lines first for alpha-beta pruning.

    Args:
        board: chess.variant.AntichessBoard — current position; used to
            classify moves and probe board state via tentative pushes.
        moves: list[chess.Move] — filtered legal moves to reorder.

    Returns:
        list[chess.Move] — same moves sorted ascending by a negated priority key
        so higher-priority moves appear first.  Chain captures (our piece lands
        on an already-attacked square after capturing) score highest, followed by
        other captures, then quiet moves that expose our pieces to the opponent.

    Antichess:
        Chain captures are the most valuable moves: they remove our piece (good)
        and place it where it will immediately be recaptured (also good), shedding
        two pieces from our inventory across two plies.  The priority key is
        negated so sorted() ascending places the highest-value move first.
    """
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
