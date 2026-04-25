"""Antichess engine: yesarch + yesstrat + yesplan.

Architecture  : bitboard operations via chess library internals.
Strategy      : inverted piece badness, capture liability, mobility.
Plan          : Watkins-derived opening book, pawn-push endgame bias.
"""

from __future__ import annotations

import chess
import chess.variant

# ── Piece "badness": cost of HAVING this piece in Antichess.
# High value = sticky / hard to get opponent to capture = bad for us.
# Bishops and queens are hardest to sacrifice; pawns are easiest.
_BADNESS: dict[int, int] = {
    chess.PAWN:   100,
    chess.KNIGHT: 220,
    chess.BISHOP: 380,  # opponent can dodge long diagonals
    chess.ROOK:   300,
    chess.QUEEN:  460,  # multipath escape makes it hardest to force-capture
    chess.KING:   150,  # short range, manageable
}

# ── Opening book (Watkins-derived key lines).
# Keys: "piece_placement turn" (first two FEN fields only).
# Values: UCI move string.
_BOOK: dict[str, str] = {
    # 1. e3 — Watkins proven win for White.
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w": "e2e3",

    # After 1.e3 — White's best responses to each Black reply.
    # 1...b6 (Liardet — hardest, 448M nodes): 2. a4 (key Watkins discovery).
    "rnbqkbnr/p1pppppp/1p6/8/8/4P3/PPPP1PPP/RNBQKBNR w": "a2a4",
    # 1...c5 (Polish — 217M nodes): 2. Qa4 hitting c6.
    "rnbqkbnr/pp1ppppp/8/2p5/8/4P3/PPPP1PPP/RNBQKBNR w": "d1a4",
    # 1...b5 (Classical — 82M nodes): 2. Ba6.
    "rnbqkbnr/p1pppppp/8/1p6/8/4P3/PPPP1PPP/RNBQKBNR w": "f1a6",
    # 1...d5: quick collapse with 2. Bb5+.
    "rnbqkbnr/ppp1pppp/8/3p4/8/4P3/PPPP1PPP/RNBQKBNR w": "f1b5",
    # 1...e6: 2. Qh5.
    "rnbqkbnr/pppp1ppp/4p3/8/8/4P3/PPPP1PPP/RNBQKBNR w": "d1h5",
    # 1...e5: 2. Qh5.
    "rnbqkbnr/pppp1ppp/8/4p3/8/4P3/PPPP1PPP/RNBQKBNR w": "d1h5",
    # 1...f5: 2. Qh5+.
    "rnbqkbnr/ppppp1pp/8/5p2/8/4P3/PPPP1PPP/RNBQKBNR w": "d1h5",
    # 1...f6: 2. e4.
    "rnbqkbnr/ppppp1pp/5p2/8/8/4P3/PPPP1PPP/RNBQKBNR w": "e3e4",
    # 1...g5: 2. Qh5.
    "rnbqkbnr/pppppp1p/8/6p1/8/4P3/PPPP1PPP/RNBQKBNR w": "d1h5",
    # 1...Nf6: 2. e4.
    "rnbqkb1r/pppppppp/5n2/8/8/4P3/PPPP1PPP/RNBQKBNR w": "e3e4",
    # 1...a5: 2. Qh5.
    "rnbqkbnr/1ppppppp/8/p7/8/4P3/PPPP1PPP/RNBQKBNR w": "d1h5",
    # 1...a6: 2. Qh5.
    "rnbqkbnr/1ppppppp/p7/8/8/4P3/PPPP1PPP/RNBQKBNR w": "d1h5",
    # 1...d6: 2. Bb5+.
    "rnbqkbnr/ppp1pppp/3p4/8/8/4P3/PPPP1PPP/RNBQKBNR w": "f1b5",
}

# ── Promotion preferences: rook is Watkins' preferred promotion piece.
_PROMO_ORDER: dict[int, int] = {
    chess.ROOK:   4,
    chess.KING:   3,
    chess.KNIGHT: 2,
    chess.QUEEN:  1,
    chess.BISHOP: 0,
    chess.PAWN:   0,
}


def _pos_key(board: chess.variant.AntichessBoard) -> str:
    """Piece-placement + turn key; ignores clocks and en passant."""
    fen = board.fen()
    parts = fen.split()
    return parts[0] + " " + parts[1]


def _iter_squares(bb: int):
    """Yield square indices from a bitboard using LSB iteration."""
    while bb:
        lsb = bb & -bb
        yield lsb.bit_length() - 1
        bb ^= lsb


def _popcount(bb: int) -> int:
    return bin(bb).count("1")


def get_pseudo_legal_moves(
    board: chess.variant.AntichessBoard,
) -> list[chess.Move]:
    """Return all pseudo-legal moves; harness filters to legal (mandatory captures)."""
    # Partition into captures and quiet so captures surface early when filtered.
    captures: list[chess.Move] = []
    quiet: list[chess.Move] = []
    for move in board.pseudo_legal_moves:
        (captures if board.is_capture(move) else quiet).append(move)
    return captures + quiet


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    """Score from side-to-move perspective. Higher = better (closer to winning).

    Antichess winning = fewer own pieces, ideally zero or stalemate.
    """
    us = board.turn
    them = not us

    our_occ = board.occupied_co[us]
    their_occ = board.occupied_co[them]

    own_badness = 0
    opp_badness = 0
    for pt, cost in _BADNESS.items():
        own_badness += _popcount(board.pieces_mask(pt, us)) * cost
        opp_badness += _popcount(board.pieces_mask(pt, them)) * cost

    own_count = _popcount(our_occ)
    opp_count = _popcount(their_occ)

    # Capture liability: own pieces the opponent CAN capture = good
    # (they may be forced to take them, reducing our piece count).
    liable = sum(
        1 for sq in _iter_squares(our_occ)
        if board.is_attacked_by(them, sq)
    )

    # How many of THEIR pieces WE can capture next move (we can threaten them).
    # High = we have forced-capture opportunities = more ways to shed pieces.
    capturable_theirs = sum(
        1 for sq in _iter_squares(their_occ)
        if board.is_attacked_by(us, sq)
    )

    score = (
        -own_badness                    # fewer/cheaper own pieces = better
        + opp_badness // 5              # opponent having pieces = slightly helpful
        + liable * 60                   # own pieces en-prise = great
        + capturable_theirs * 20        # our attack options = useful
        + (16 - own_count) * 40         # raw piece-count bonus for having fewer
        - (16 - opp_count) * 10         # prefer opponent to have more pieces
    )

    return score


def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    """Order: opening book first, then promotions, captures, quiet (pawn pushes)."""
    # Check opening book.
    key = _pos_key(board)
    book_uci = _BOOK.get(key)
    if book_uci:
        book_move = chess.Move.from_uci(book_uci)
        if book_move in moves:
            rest = [m for m in moves if m != book_move]
            return [book_move] + _sort_non_book(board, rest)

    return _sort_non_book(board, moves)


def _sort_non_book(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    promotions: list[chess.Move] = []
    captures: list[chess.Move] = []
    quiet: list[chess.Move] = []

    for move in moves:
        if move.promotion is not None:
            promotions.append(move)
        elif board.is_capture(move):
            captures.append(move)
        else:
            quiet.append(move)

    # Promotions: rook first (Watkins), king second, knight third.
    promotions.sort(key=lambda m: _PROMO_ORDER.get(m.promotion or chess.PAWN, 0), reverse=True)

    # Captures: prefer sacrificing our own sticky pieces (queens/bishops),
    # and prefer capturing opponent's least-sticky pieces (pawns) so they
    # recapture us, helping shed our pieces in return.
    def cap_score(m: chess.Move) -> int:
        own_pt = board.piece_type_at(m.from_square)
        own_val = _BADNESS.get(own_pt, 0) if own_pt else 0
        opp_pt = board.piece_type_at(m.to_square)
        # En passant: to_square is empty but it's a pawn capture.
        opp_val = _BADNESS.get(opp_pt, _BADNESS[chess.PAWN]) if opp_pt else _BADNESS[chess.PAWN]
        # High own piece sacrificed = great (shed sticky piece).
        # Low opponent piece captured = good (they'll recapture, shedding ours).
        return own_val * 2 - opp_val

    captures.sort(key=cap_score, reverse=True)

    # Quiet moves: favour pawn advances (endgame-breaking heuristic from Watkins).
    def quiet_score(m: chess.Move) -> int:
        pt = board.piece_type_at(m.from_square)
        if pt == chess.PAWN:
            rank = chess.square_rank(m.to_square)
            return rank if board.turn == chess.WHITE else (7 - rank)
        return 0

    quiet.sort(key=quiet_score, reverse=True)

    return promotions + captures + quiet
