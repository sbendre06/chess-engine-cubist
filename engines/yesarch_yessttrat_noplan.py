"""Antichess engine: yesarch_yessttrat_noplan

Architecture:  returns list(board.legal_moves) — lets python-chess handle
               the mandatory-capture rule correctly.
Strategy:      inverted piece burden evaluation + capture-liability bonus +
               move ordering that prioritises sacrificing heavy pieces.
Planning:      none (no opening book, no tablebase).
"""

from __future__ import annotations

import chess
import chess.variant

# ---------------------------------------------------------------------------
# Piece burden table
# In Antichess the goal is to *lose* all pieces.  A piece you hold is a
# burden; higher = harder to give away / more dangerous to possess.
#
# Key insights from Watkins (2016) and Antichess theory:
#   - Bishops are the worst piece: a lone bishop can be forced to eat the
#     opponent's entire army one capture at a time, handing them the win.
#   - Rooks share a similar forced-capture-chain vulnerability.
#   - Queens have multipath escape routes and are harder to trap.
#   - Kings are surprisingly useful as drawing tools (short range).
#   - Pawns are the cheapest sacrifice; promoting removes them too.
# ---------------------------------------------------------------------------
PIECE_BURDEN: dict[int, int] = {
    chess.PAWN:   100,
    chess.KNIGHT: 250,
    chess.QUEEN:  300,   # better defensively — can escape forced chains
    chess.KING:   175,   # short range, useful drawing tool
    chess.ROOK:   400,   # linear forced-chain liability
    chess.BISHOP: 450,   # worst piece in Antichess
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
        board.legal_moves regardless, so this is both correct and safe.
        AntichessBoard.legal_moves also handles promotion-to-king, no-castling,
        and king-capturable rules that differ from standard chess.
    """
    return list(board.legal_moves)


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    """Score the position from the side-to-move perspective.

    Higher score → better for the side to move.

    Args:
        board: chess.variant.AntichessBoard — current position; board.turn
            identifies which side is evaluated (me/opp).

    Returns:
        int — side-to-move-positive score.  Components:
        (1) opp_burden - my_burden: material burden delta where each piece
            type is weighted by how hard it is to sacrifice (PIECE_BURDEN),
            not classical piece strength;
        (2) PIECE_BURDEN[pt] // 3 per own piece currently attacked by the
            opponent: capture-liability bonus for pieces that will soon be taken.
        Terminal positions are scored by the harness with MATE_SCORE.

    Antichess:
        PIECE_BURDEN weights reflect sacrifice difficulty: bishops (450) and
        rooks (400) are worst because they can be trapped in forced capture
        chains; queens (300) are better because their multipath mobility lets
        them escape chains.  If a capture is available the opponent is forced
        to take, so own attacked pieces will soon be removed — this is good.
    """
    me  = board.turn
    opp = not me

    # --- 1. Material burden ---
    my_burden  = sum(PIECE_BURDEN[pt] * len(board.pieces(pt, me))
                     for pt in PIECE_BURDEN)
    opp_burden = sum(PIECE_BURDEN[pt] * len(board.pieces(pt, opp))
                     for pt in PIECE_BURDEN)

    score = opp_burden - my_burden

    # --- 2. Capture-liability bonus ---
    # Each of my pieces that is under attack by the opponent is "en prise"
    # and may be forcibly taken, removing it from my inventory.
    for pt in PIECE_BURDEN:
        for sq in board.pieces(pt, me):
            if board.is_attacked_by(opp, sq):
                # ~1/3 of full burden as a bonus; avoids dominating the material term
                score += PIECE_BURDEN[pt] // 3

    return score


def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    """Reorder moves to improve alpha-beta cut-offs.

    Args:
        board: chess.variant.AntichessBoard — current position; used to
            classify moves, look up piece burdens, and probe recapturability
            via board.push/pop.
        moves: list[chess.Move] — filtered legal moves to reorder.

    Returns:
        list[chess.Move] — captures sorted by capture_key, followed by non-
        captures sorted by non_capture_key.  Captures always precede non-captures.
        Within captures, chain sacrifices (immediately recapturable after the
        move) score +2000 on top of own-piece burden; within non-captures,
        moves to pre-attacked squares score +1500 on top of own-piece burden.

    Antichess ordering heuristics
    ------------------------------
    Captures (always explored first):
      - Prefer to capture *with* a high-burden piece (getting rid of it).
      - Add a large bonus if our piece will be immediately recapturable after
        the capture (chain sacrifice: we lose the heavy piece we wanted gone).

    Non-captures:
      - Prefer moves that place our piece on a square attacked by the opponent
        (it will likely be taken on the next ply).
      - Among those, prefer moving heavier pieces into danger.

    Antichess:
        Capture ordering uses own-attacker burden, not victim value: the goal
        is to shed our hardest-to-lose pieces.  The recapture check (board.push
        + is_attacked_by + board.pop) is done per-capture and is the most
        expensive part of the ordering; it is justified because chain sacrifices
        are the highest-leverage moves in antichess.
    """
    opp = not board.turn

    captures:     list[chess.Move] = []
    non_captures: list[chess.Move] = []

    for move in moves:
        if board.is_capture(move):
            captures.append(move)
        else:
            non_captures.append(move)

    # -- Score captures --
    def capture_key(move: chess.Move) -> int:
        our_type   = board.piece_type_at(move.from_square)
        our_burden = PIECE_BURDEN.get(our_type, 0)

        # After the capture, is our piece recapturable by the opponent?
        board.push(move)
        # board.turn has flipped to the opponent after push
        recapturable = board.is_attacked_by(board.turn, move.to_square)
        board.pop()

        # Large bonus for being immediately recapturable (chain sacrifice)
        recapture_bonus = 2000 if recapturable else 0

        # Lower (more negative) key → sorted earlier → explored first
        return -(our_burden + recapture_bonus)

    # -- Score non-captures --
    def non_capture_key(move: chess.Move) -> int:
        our_type   = board.piece_type_at(move.from_square)
        our_burden = PIECE_BURDEN.get(our_type, 0)

        # Will the destination square be attacked by the opponent after we move?
        # Use a pre-move approximation (no push needed → fast).
        en_prise = board.is_attacked_by(opp, move.to_square)

        en_prise_bonus = 1500 if en_prise else 0
        return -(our_burden + en_prise_bonus)

    sorted_captures     = sorted(captures,     key=capture_key)
    sorted_non_captures = sorted(non_captures, key=non_capture_key)

    # Captures always come before non-captures
    return sorted_captures + sorted_non_captures
