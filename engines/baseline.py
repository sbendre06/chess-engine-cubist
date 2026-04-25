"""Baseline reference antichess engine.

Hand-written, not AI-generated. The yardstick every ablation-branch engine
is scored against. Ported verbatim from the original main.py AI-edit hooks
(get_pseudo_legal_moves, evaluate_board) plus a simple capture-first
order_moves that mirrors the harness's prior built-in ordering.
"""

from __future__ import annotations

import chess
import chess.variant


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 400,
}


def get_pseudo_legal_moves(board: chess.variant.AntichessBoard) -> list[chess.Move]:
    """Return candidate moves, enforcing antichess's forced-capture rule.

    Args:
        board: chess.variant.AntichessBoard — current position including turn,
            piece placement, and en-passant state.

    Returns:
        list[chess.Move] — if any pseudo-legal capture exists, only captures
        are returned; otherwise all pseudo-legal moves are returned.

    Antichess:
        Implements the forced-capture rule manually by scanning
        board.pseudo_legal_moves for captures and excluding quiet moves when
        any capture is found.  The harness re-filters through board.legal_moves
        before playing any move, but this function must express the rule so the
        search only considers captures when they exist.
    """
    moves = list(board.pseudo_legal_moves)
    captures = [move for move in moves if board.is_capture(move)]
    return captures if captures else moves


def evaluate_board(board: chess.variant.AntichessBoard) -> int:
    """Antichess heuristic from the side-to-move perspective.

    Material and mobility signs are INVERTED vs classical chess:
      - Fewer own pieces is better (closer to the win condition).
      - Fewer own moves is better (harder to be forced).
      - Capture availability for opponent is good (they must take).

    Args:
        board: chess.variant.AntichessBoard — current position; board.turn
            identifies which side is being evaluated.

    Returns:
        int — side-to-move-positive score.  Components: +150 per piece
        advantage (opp_pieces - own_pieces), +material delta/10, -4 per own
        legal move, +4 per opponent legal move, -12 per own capture available,
        +12 per opponent capture available.  Terminal positions are scored by
        the harness with MATE_SCORE; not handled here.

    Antichess:
        Every classical heuristic is inverted: own material is a liability,
        own mobility is bad, opponent mobility is good, own captures available
        are bad (we'd rather not have forced choices), opponent captures are
        good (they must take).
    """
    side = board.turn
    opp = not side

    own_material = 0
    opp_material = 0
    own_pieces = 0
    opp_pieces = 0
    for piece in board.piece_map().values():
        value = PIECE_VALUES[piece.piece_type]
        if piece.color == side:
            own_material += value
            own_pieces += 1
        else:
            opp_material += value
            opp_pieces += 1

    own_moves = get_pseudo_legal_moves(board)
    opp_probe = board.copy(stack=False)
    opp_probe.turn = opp
    opp_moves = get_pseudo_legal_moves(opp_probe)

    own_capture_count = sum(1 for move in own_moves if board.is_capture(move))
    opp_capture_count = sum(1 for move in opp_moves if opp_probe.is_capture(move))

    return (
        150 * (opp_pieces - own_pieces)
        + (opp_material - own_material) // 10
        - 4 * len(own_moves)
        + 4 * len(opp_moves)
        - 12 * own_capture_count
        + 12 * opp_capture_count
    )


def _capture_value(board: chess.variant.AntichessBoard, move: chess.Move) -> int:
    if not board.is_capture(move):
        return 0
    captured = board.piece_at(move.to_square)
    if captured is not None:
        return PIECE_VALUES.get(captured.piece_type, 0)
    if board.is_en_passant(move):
        return PIECE_VALUES[chess.PAWN]
    return 0


def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    """Reorder moves with captures first (biggest victim first), then promotions, then quiets.

    Args:
        board: chess.variant.AntichessBoard — current position; used to
            classify moves and look up captured-piece values.
        moves: list[chess.Move] — filtered legal moves to reorder.

    Returns:
        list[chess.Move] — same moves sorted by descending priority tuple:
        (is_capture, is_promotion, captured_piece_value, promotion_piece_value).
        Captures of the highest-value victim appear first; among ties,
        promotions to higher-value pieces are preferred.

    Antichess:
        Sorting by victim value (classical MVV) is used as a simple heuristic
        even though in antichess we want the opponent to keep their heavy pieces.
        This baseline deliberately keeps ordering straightforward; more
        antichess-aware orderings appear in the ablation-branch engines.
    """
    return sorted(
        moves,
        key=lambda move: (
            1 if board.is_capture(move) else 0,
            1 if move.promotion is not None else 0,
            _capture_value(board, move),
            PIECE_VALUES.get(move.promotion, 0),
        ),
        reverse=True,
    )
