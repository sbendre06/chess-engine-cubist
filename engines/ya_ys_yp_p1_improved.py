"""Antichess engine: ya_ys_yp_p1_improved

Improvements over yesarch_yesstrat_yesplan_p1 (previous best engine):

  1. Antichess-correct piece badness (Bishop > Queen), derived from Watkins §4:
     "Bishops are thought to be the worst pieces, as they can often be forced
     to take a large army one-by-one."  Queens "can more often get out of
     forced capture sequences by simultaneously threatening multiple enemy
     units" → somewhat less stuck.  The original engine had this inverted.

  2. Redesigned evaluate_board — three key changes over p1:
     a) Relative piece count: (opp_count − our_count) * (250 + endgame_amp*15).
        Using a large RELATIVE weight (not absolute) means having fewer pieces
        than the opponent is strongly and correctly rewarded, with endgame
        amplification.  Removing the old `(16−own)` absolute term and the
        spurious `opp_bad//5` term eliminates the "king-oscillation" bug where
        returning a king and keeping a pawn appeared better than promoting.
     b) Central pawn double-credit: d/e file pawns score 2× advancement bonus.
        After 1.e3 the e-pawn opens the f1 bishop diagonal; h2h3 opens nothing.
     c) Piece mobility: each reachable square for own non-pawn pieces scores +3.
        Differentiates open positions (e.g. post-1.e3 the Bf1 gains 5 squares)
        from closed ones (h2h3 gives 0 new bishop squares).

  3. Badness-weighted capture liability and capture pressure: a bishop sitting
     under opponent attack is worth more than a pawn under attack because
     shedding the sticky piece is the whole point of antichess.

  4. Terminal detection in evaluate_board: immediate ±50 000 for wins/losses
     so that the harness's timeout path produces correct results.

  5. Extended and corrected Watkins opening book (Watkins 2016, lcsolved.md):
       - Fixes 1.e3 b5 → f1b5 (Bxb5), which is the ONLY legal move (forced
         capture); the old entry f1a6 was illegal and silently ignored.
       - Adds all 20 Level-1 White responses (covers every Black first move).
       - Adds 1.e3 Nc6 → Ba6 (Balkan Defence, §5.3).
       - Adds 1.e3 Nh6 → Ba6 (Hippopotamus, §5.5).
       - Adds critical Level-2 follow-ups: Bxd7 after Nh6, Qh5 after bxa6,
         and the forced axb5 continuation in the Liardet Defence.
       - Replaces 1.e3 c5 Qa4 with the correct Bb5 (§5.8 mainline).

  6. Chain-depth move ordering: reward landing squares attacked by multiple
     opponent pieces.  Each extra attacker is one more forced-recapture link
     in a chain.  Base bonus 1 000, plus 400 per additional attacker.

  7. Immediate-win detection: if we have exactly one piece left and we capture
     onto a square attacked by at least one opponent piece, the opponent must
     recapture us → we reach 0 pieces → antichess win.  Gets a +99 000 bonus.

  8. Promotion priority ordering: rook first (Watkins §4 preferred promoter),
     then king (short-range, hard to force-capture elsewhere), then knight,
     queen, bishop.  Removes dangerous rook/queen promotions that allow
     Black to manoeuvre to a rank-8 square forcing recapture → Black wins.
"""

from __future__ import annotations

import chess
import chess.variant

# ── Piece badness: cost of US owning a piece of this type. ────────────────────
# Higher badness → harder to shed → worse for us to hold.
#
# Watkins §4 ranking (worst to best for antichess):
#   Bishop > Rook ≈ Queen > Knight > King > Pawn
#
# Bishop: long diagonals that opponents can easily dodge; gets trapped in
#   forced-capture chains against entire armies.
# Queen: multi-directional escape routes make it slightly less sticky.
# Rook: similar stickiness to bishop on open files/ranks, but "piece of
#   choice when promoting" (Watkins §4), so slightly lower badness.
# Knight: short range, limited tempo capacity.
# King: short range → stable, manageable → low badness.
# Pawn: push toward promotion; the canonical antichess endgame tool.
_BADNESS: dict[int, int] = {
    chess.PAWN:   90,
    chess.KNIGHT: 240,
    chess.BISHOP: 450,   # Watkins §4: worst piece
    chess.ROOK:   320,
    chess.QUEEN:  410,   # can escape via multi-path threats
    chess.KING:   160,
}

# Promotion priority.  Rook is Watkins' preferred endgame promoter (§4).
# King comes second (short range → hardest for opponent to force-capture).
_PROMO_ORDER: dict[int, int] = {
    chess.ROOK:   5,
    chess.KING:   4,
    chess.KNIGHT: 3,
    chess.QUEEN:  2,
    chess.BISHOP: 1,
}

# ── Watkins opening book ──────────────────────────────────────────────────────
# Keys: piece-placement + " " + side-to-move (first two FEN fields only;
# clocks, castling rights, and en-passant are stripped for robustness).
# Values: UCI move strings.
#
# Sources: Watkins 2016 "Losing Chess: 1.e3 wins for White" (lcsolved.md),
# §5.1–§5.9.  Node counts in comments are from Table 1.
_BOOK: dict[str, str] = {
    # 1.e3 — the proven White win (entire paper)
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w": "e2e3",

    # ── Level 1: White's response to each of Black's 20 first moves ──────────

    # 1...b6 (Liardet Defence, 448 M nodes): 2.a4
    # The 2015 breakthrough (§5.9): 2.Ba6 didn't work; 2.a4 is the winning try.
    "rnbqkbnr/p1pppppp/1p6/8/8/4P3/PPPP1PPP/RNBQKBNR w": "a2a4",

    # 1...c5 (Polish/Goldovski, 217 M nodes): 2.Bb5
    # Watkins §5.8: "1.e3 c5 2.Bb5 Qc7 3.Bxd7 Bxd7 4.Qf3..."
    "rnbqkbnr/pp1ppppp/8/2p5/8/4P3/PPPP1PPP/RNBQKBNR w": "f1b5",

    # 1...b5 (Classical, 82 M nodes): 2.Bxb5 — FORCED CAPTURE
    # The f1-bishop can reach b5 via e2-d3-c4 (e2 freed by 1.e3).
    # Bxb5 is the only legal capture, so White is forced to play it.
    # The old entry (f1a6 = Ba6) was illegal and silently skipped.
    "rnbqkbnr/p1pppppp/8/1p6/8/4P3/PPPP1PPP/RNBQKBNR w": "f1b5",

    # 1...g5 (Wild Boar Attack, 45.5 M): 2.Qh5
    "rnbqkbnr/pppppp1p/8/6p1/8/4P3/PPPP1PPP/RNBQKBNR w": "d1h5",

    # 1...e6 (Modern Defence, 43 M): 2.Qh5 → Watkins' Qxf7 line (§5.7)
    "rnbqkbnr/pppp1ppp/4p3/8/8/4P3/PPPP1PPP/RNBQKBNR w": "d1h5",

    # 1...e5: 2.Qh5
    "rnbqkbnr/pppp1ppp/8/4p3/8/4P3/PPPP1PPP/RNBQKBNR w": "d1h5",

    # 1...f5: 2.Qh5
    "rnbqkbnr/ppppp1pp/8/5p2/8/4P3/PPPP1PPP/RNBQKBNR w": "d1h5",

    # 1...f6: 2.e4 (open the bishop diagonal)
    "rnbqkbnr/ppppp1pp/5p2/8/8/4P3/PPPP1PPP/RNBQKBNR w": "e3e4",

    # 1...Nc6 (Balkan Defence, 10.7 M): 2.Ba6
    # Black's b7 pawn is forced to capture bxa6 (§5.3).
    "r1bqkbnr/pppppppp/2n5/8/8/4P3/PPPP1PPP/RNBQKBNR w": "f1a6",

    # 1...Nh6 (Hippopotamus, 17.5 M): 2.Ba6
    # Black's b7 pawn is forced to capture bxa6 (§5.5).
    "rnbqkb1r/pppppppp/7n/8/8/4P3/PPPP1PPP/RNBQKBNR w": "f1a6",

    # 1...c6: 2.Bb5
    # Black's c6 pawn is forced to capture cxb5 (§5.2 mainline entry).
    "rnbqkbnr/pp1ppppp/2p5/8/8/4P3/PPPP1PPP/RNBQKBNR w": "f1b5",

    # 1...a5: 2.Qh5
    "rnbqkbnr/1ppppppp/8/p7/8/4P3/PPPP1PPP/RNBQKBNR w": "d1h5",

    # 1...a6: 2.Qh5
    "rnbqkbnr/1ppppppp/p7/8/8/4P3/PPPP1PPP/RNBQKBNR w": "d1h5",

    # 1...d5 (trivial refutation, 33 nodes): 2.Bb5 threatens Bxd7
    "rnbqkbnr/ppp1pppp/8/3p4/8/4P3/PPPP1PPP/RNBQKBNR w": "f1b5",

    # 1...d6 (trivial, 33 nodes): 2.Bb5 threatens Bxd7 (d6 clears d7)
    "rnbqkbnr/ppp1pppp/3p4/8/8/4P3/PPPP1PPP/RNBQKBNR w": "f1b5",

    # 1...Nf6: 2.e4
    "rnbqkb1r/pppppppp/5n2/8/8/4P3/PPPP1PPP/RNBQKBNR w": "e3e4",

    # 1...h5: 2.Qh5
    "rnbqkbnr/ppppppp1/8/7p/8/4P3/PPPP1PPP/RNBQKBNR w": "d1h5",

    # 1...h6: 2.Qh5
    "rnbqkbnr/ppppppp1/7p/8/8/4P3/PPPP1PPP/RNBQKBNR w": "d1h5",

    # 1...g6: 2.Qh5
    "rnbqkbnr/pppppp1p/6p1/8/8/4P3/PPPP1PPP/RNBQKBNR w": "d1h5",

    # 1...Na6: 2.Ba6 — b7 pawn is forced to capture bxa6
    "r1bqkbnr/pppppppp/n7/8/8/4P3/PPPP1PPP/RNBQKBNR w": "f1a6",

    # ── Level 2: critical follow-ups from the Watkins proof tree ─────────────

    # After 1.e3 b5 2.Bxb5 Nh6: 3.Bxd7 — FORCED (only capture)
    # Watkins §5.4.1: "1.e3 b5 2.Bxb5 Nh6 3.Bxd7 Nxd7 4.e4"
    "rnbqkb1r/p1pppppp/7n/1B6/8/4P3/PPPP1PPP/RNBQK1NR w": "b5d7",

    # After 3.Bxd7 Nxd7 (Nb8→d7): 4.e4
    "r1bqkb1r/p1pnpppp/7n/8/8/4P3/PPPP1PPP/RNBQK1NR w": "e3e4",

    # After 1.e3 Nc6 2.Ba6 bxa6: 3.a4
    # Watkins §5.3: "1.e3 Nc6 2.Ba6 bxa6 3.a4 Nd4 4.exd4..."
    "r1bqkbnr/p1pppppp/p1n5/8/8/4P3/PPPP1PPP/RNBQK1NR w": "a2a4",

    # After 1.e3 Nh6 2.Ba6 bxa6: 3.Qh5
    # Watkins §5.5: "1.e3 Nh6 2.Ba6 bxa6 3.Qh5 g6/c5..."
    "rnbqkb1r/p1pppppp/p6n/8/8/4P3/PPPP1PPP/RNBQK1NR w": "d1h5",

    # After 1.e3 b6 2.a4 b5: 3.axb5 — FORCED capture
    "rnbqkbnr/p1pppppp/1p6/1p6/P7/4P3/1PPP1PPP/RNBQKBNR w": "a4b5",
}


def _pos_key(board: chess.variant.AntichessBoard) -> str:
    """Two-field FEN key: piece placement + side to move."""
    fen = board.fen()
    parts = fen.split()
    return parts[0] + " " + parts[1]


def get_pseudo_legal_moves(
    board: chess.variant.AntichessBoard,
) -> list[chess.Move]:
    """Return legal moves, captures first.

    The harness filters our output through board.legal_moves; returning captures
    first ensures they surface correctly after filtering.
    """
    captures: list[chess.Move] = []
    quiet: list[chess.Move] = []
    for move in board.legal_moves:
        (captures if board.is_capture(move) else quiet).append(move)
    return captures + quiet


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    """Score from the side-to-move perspective. Higher = closer to winning.

    Antichess inversion: fewer / cheaper own pieces = better.

    Key heuristics (from Watkins §4 and general antichess theory):
      • Relative piece count: the primary signal. Having fewer own pieces than
        the opponent is strongly rewarded, with endgame amplification. Using
        a relative (opp-our) term avoids the oscillation bug where "return the
        king and keep the pawn" tricks the evaluator into thinking it's better
        than promoting.
      • Capture liability: own pieces under opponent attack are GOOD — they
        may be forced to capture us, shedding our sticky piece.
      • Pawn advancement: advanced pawns break endgame stalemates (§3.2.1).
        Central pawns (d/e files) score double: they open key diagonals for
        bishop/queen deployment faster.
      • Piece mobility: more reachable squares = more forced-capture options.
        After 1.e3 the f1 bishop gains 5+ squares; h2h3 gives it nothing,
        differentiating central from edge pawn openings.
    """
    if board.is_game_over():
        outcome = board.outcome()
        if outcome and outcome.winner == board.turn:
            return 50_000
        if outcome and outcome.winner is not None:
            return -50_000
        return 0

    us = board.turn
    them = not us

    our_occ = board.occupied_co[us]
    their_occ = board.occupied_co[them]

    our_count = chess.popcount(our_occ)
    opp_count = chess.popcount(their_occ)

    # Badness-weighted own material only (no opp_bad term to avoid oscillation).
    own_bad: int = 0
    for pt, cost in _BADNESS.items():
        own_bad += chess.popcount(board.pieces_mask(pt, us)) * cost

    # Capture liability: own pieces under opponent attack, weighted by badness.
    # A bishop sitting in opponent fire is worth far more than a pawn there.
    liable_bad: int = 0
    for sq in chess.scan_forward(our_occ):
        if board.is_attacked_by(them, sq):
            pt = board.piece_type_at(sq)
            liable_bad += _BADNESS.get(pt, 90)  # type: ignore[arg-type]

    # Capture pressure: opponent pieces we can currently attack, weighted.
    # Attacking a sticky opponent piece = we can force a favourable chain.
    pressure_bad: int = 0
    for sq in chess.scan_forward(their_occ):
        if board.is_attacked_by(us, sq):
            pt = board.piece_type_at(sq)
            pressure_bad += _BADNESS.get(pt, 90)  # type: ignore[arg-type]

    # Pawn advancement (Watkins §3.2.1 and §4: the canonical endgame tool).
    # Central pawns (d=file 3, e=file 4) score double: they open long diagonals
    # for bishop/queen deployment that edge pawns cannot.
    pawn_advance: int = 0
    for sq in chess.scan_forward(board.pieces_mask(chess.PAWN, us)):
        rank = chess.square_rank(sq)
        file = chess.square_file(sq)
        advance = rank if us == chess.WHITE else (7 - rank)
        pawn_advance += advance
        if file in (3, 4):   # d=3, e=4: central pawn gets extra weight
            pawn_advance += advance

    # Piece mobility: reachable squares for each non-pawn own piece.
    # After e.g. 1.e3 the f1 bishop has 5+ new squares; after 1.h3 it has 0.
    # Higher mobility → more capture-chain forcing opportunities.
    own_mobility: int = 0
    pawn_bb = board.pieces_mask(chess.PAWN, us)
    for sq in chess.scan_forward(our_occ & ~pawn_bb):
        own_mobility += chess.popcount(board.attacks_mask(sq) & ~our_occ)

    # Endgame amplification: as pieces leave the board each remaining piece
    # matters more (e.g. K vs K+P is much more urgent than 16 vs 16).
    total = our_count + opp_count
    endgame_amp = max(0, 16 - total)   # 0 at start, up to ~30 in bare endgame

    score = (
        -own_bad                                               # sticky own pieces = bad
        + (liable_bad * 55) // 100                            # own en-prise = great
        + (pressure_bad * 15) // 100                          # we can attack = options
        + (opp_count - our_count) * (250 + endgame_amp * 15)  # relative piece count
        + pawn_advance * 8                                     # advance pawns (central 2×)
        + own_mobility * 3                                     # mobility bonus
    )
    return score


def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    """Order moves: opening book → promotions → captures (chain-aware) → pawn pushes."""
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
    them = not board.turn
    own_count = chess.popcount(board.occupied_co[board.turn])

    def score_move(move: chess.Move) -> int:
        s = 0

        # Promotions are always high priority regardless of capture/quiet.
        if move.promotion is not None:
            s += 2000 + _PROMO_ORDER.get(move.promotion, 0) * 100

        if board.is_capture(move):
            attacker_type = board.piece_type_at(move.from_square)
            attacker_bad = _BADNESS.get(attacker_type, 90)  # type: ignore[arg-type]

            # MVA (Most Valuable/Stickiest Attacker first): sacrifice our
            # hardest-to-shed piece — bishops and queens otherwise get stuck.
            s += attacker_bad * 2

            # Chain-depth bonus: count how many opponent pieces attack our
            # landing square.  Each attacker is one more link in a
            # forced-recapture chain (they must capture us, shedding their
            # piece; the next attacker then must capture them, etc.).
            try:
                chain = chess.popcount(
                    board.attackers_mask(them, move.to_square)
                )
            except AttributeError:
                # python-chess fallback if attackers_mask is unavailable.
                chain = int(board.is_attacked_by(them, move.to_square))

            if chain > 0:
                # Base chain bonus + extra per additional attacker.
                s += 1000 + chain * 400

            # Immediate-win detection: if this is our last piece and we
            # land in opponent fire, they must recapture → 0 own pieces → win.
            if own_count == 1 and chain > 0:
                s += 99_000

        else:
            # Quiet moves: pawn pushes ranked by rank advancement (Watkins).
            pt = board.piece_type_at(move.from_square)
            if pt == chess.PAWN:
                rank = chess.square_rank(move.to_square)
                adv = rank if board.turn == chess.WHITE else (7 - rank)
                s += adv * 12

        return s

    return sorted(moves, key=score_move, reverse=True)
