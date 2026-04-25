"""Antichess engine: yesarch-nostrat-yesplan."""
from __future__ import annotations

import chess
import chess.variant

# How hard each piece is to sacrifice in Antichess (higher = more persistent = worse to have).
# Pawns are stubbornest (limited movement, diagonal-only capture); queens are most mobile.
_PIECE_WEIGHT: dict[int, int] = {
    chess.PAWN: 200,
    chess.KNIGHT: 130,
    chess.BISHOP: 130,
    chess.KING: 150,
    chess.ROOK: 90,
    chess.QUEEN: 50,
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
    return list(board.legal_moves)


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    """Score the position from the side-to-move perspective using inverted piece weight.

    Args:
        board: chess.variant.AntichessBoard — current position; board.turn
            identifies which side is being evaluated.

    Returns:
        int — side-to-move-positive score.  If the game is over, returns
        ±900_000 (win/loss sentinel).  Otherwise: sum of (opp_weight - own_weight)
        per piece type (inverted material), minus 20 per own legal move (mobility
        penalty), plus 40 per own piece currently attacked by the opponent
        (capture-threat bonus).

    Antichess:
        _PIECE_WEIGHT encodes how hard each type is to sacrifice (pawns hardest,
        queens easiest).  Mobility is penalised because fewer options means the
        opponent can force captures on us more easily, and stalemate (zero moves)
        is a win.  The terminal check here handles the case where evaluate_board
        is called on a timeout mid-search (harness/engine.py line 136).
    """
    # Fallback terminal check: harness normally uses _terminal_score, but evaluate_board
    # is also called mid-search on timeout (harness/engine.py line 136).
    if board.is_game_over(claim_draw=True):
        outcome = board.outcome(claim_draw=True)
        if outcome is None or outcome.winner is None:
            return 0
        return 900_000 if outcome.winner == board.turn else -900_000

    score = 0

    # Inverted material: fewer own pieces = better; more opponent pieces = better
    # (opponent has more to give away, is further from winning).
    for pt in chess.PIECE_TYPES:
        w = _PIECE_WEIGHT[pt]
        score -= len(board.pieces(pt, board.turn)) * w
        score += len(board.pieces(pt, not board.turn)) * w

    # Mobility penalty: 0 moves = stalemate = WIN; penalise every extra option.
    score -= len(list(board.legal_moves)) * 20

    # Attack bonus: own pieces under opponent attack will be captured next move.
    score += sum(
        1 for sq in chess.SquareSet(board.occupied_co[board.turn])
        if board.is_attacked_by(not board.turn, sq)
    ) * 40

    return score


def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    """Reorder moves to place more promising lines first for alpha-beta pruning.

    Args:
        board: chess.variant.AntichessBoard — current position; used to
            classify moves and look up piece weights and attack state.
        moves: list[chess.Move] — filtered legal moves to reorder.

    Returns:
        list[chess.Move] — same moves sorted ascending by a negated key so
        higher-priority moves appear first.  Captures score by own piece weight
        plus half the captured piece's weight; promotions add +150.  Quiet moves
        to opponent-attacked squares score own weight + 100; pawn advances add 50.

    Antichess:
        Capture ordering uses own-piece weight as the primary term: we want to
        sacrifice our hardest-to-lose piece (heaviest weight) first.  Moving to
        opponent-attacked squares on quiet moves is rewarded because it sets up
        a forced capture next ply.  Promotions score positively because converting
        a stubborn pawn into a more-sacrificeable piece advances our goal.
    """
    def key(move: chess.Move) -> int:
        val = 0
        moving = board.piece_at(move.from_square)
        moving_w = _PIECE_WEIGHT.get(moving.piece_type, 100) if moving else 100

        if board.is_capture(move):
            # En passant: captured pawn is not on to_square.
            if board.is_en_passant(move):
                captured_w = _PIECE_WEIGHT[chess.PAWN]
            else:
                captured = board.piece_at(move.to_square)
                captured_w = _PIECE_WEIGHT.get(captured.piece_type, 100) if captured else 100
            # Prefer sacrificing our heaviest pieces; mildly prefer capturing heavy opponents.
            val += moving_w + captured_w // 2
        else:
            # Move piece to a square the opponent already attacks → it'll be captured.
            if board.is_attacked_by(not board.turn, move.to_square):
                val += moving_w + 100
            # Advance pawns to create diagonal capture opportunities.
            if moving and moving.piece_type == chess.PAWN:
                val += 50

        # Pawn promotion replaces a stubborn pawn with a more-sacrificeable piece.
        if move.promotion:
            val += 150

        return -val  # negate: sorted ascending, so higher val = tried first

    return sorted(moves, key=key)
