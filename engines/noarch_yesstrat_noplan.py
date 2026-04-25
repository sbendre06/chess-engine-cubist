"""noarch_yesstrat_noplan — Antichess engine with strategy, no architecture, no planning phase.

Strategy based on Mark Watkins' proof insights:
- Fewer own pieces is better (goal: lose all)
- Mobility matters: more legal moves = more control
- Piece-type values inverted: bishops worst (can be forced to eat entire army),
  queens defensively strong (multipath escape), kings surprisingly useful
- Prioritize captures that offload our worst pieces
- Expose pieces to capture; push pawns to promote/disrupt
"""

from __future__ import annotations

import chess
import chess.variant

# Antichess piece "burden" values — how bad it is to STILL HAVE this piece.
# Higher burden = we want to lose it first / it's worth more to sacrifice.
# Inverted from standard chess: bishops are the worst (highest burden),
# rooks are also bad. Queens are moderate (they can escape capture chains).
# Kings are low burden (useful as drawing tools). Pawns are moderate.
_BURDEN: dict[int, int] = {
    chess.PAWN:   20,
    chess.KNIGHT: 30,
    chess.BISHOP: 60,   # worst — can be forced to eat everything
    chess.ROOK:   50,   # bad but often useful as promotion target
    chess.QUEEN:  25,   # good defensive escape ability
    chess.KING:   10,   # surprisingly useful, low burden
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
        filters through board.legal_moves before playing, discarding quiet moves
        whenever a capture exists.

    Antichess:
        Returns pseudo-legals so the harness's legal-move filter handles the
        forced-capture rule.  The search sees a superset of legal candidates;
        the harness silently prunes non-captures when a capture is mandatory.
    """
    return list(board.pseudo_legal_moves)


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    """Score the position from the side-to-move perspective.

    Higher = better for the side to move (i.e., closer to winning).

    Args:
        board: chess.variant.AntichessBoard — current position; board.turn
            identifies which side is evaluated.

    Returns:
        int — side-to-move-positive score.  If the game is over, returns
        ±1_000_000.  Otherwise composed of: -3 * own_burden + opp_burden
        (inverted material), -15 * own_count + 5 * opp_count (piece-count
        terms), +2 * mobility (legal-move count), pawn advancement bonus,
        and a stalemate proximity bonus (when own_count ≤ 3 and mobility < 5).

    Key axes:
    1. Own material burden: fewer/lighter pieces = better (want to lose them)
    2. Opponent material burden: more/heavier = neutral-to-good (they still need to lose theirs)
    3. Mobility: more legal moves for us = better (control over what gets captured)
    4. Stalemate proximity: if we have very few pieces and limited moves, that's great

    Antichess:
        Terminal positions are handled here by returning ±1_000_000, not
        delegated to the harness; this covers the timeout path where evaluate_board
        is called mid-search.  The stalemate proximity bonus is specific to
        antichess: zero legal moves is a win for the stalemated side.
    """
    if board.is_game_over(claim_draw=True):
        outcome = board.outcome(claim_draw=True)
        if outcome is None or outcome.winner is None:
            return 0
        # Winning means we (side to move at THIS point) won
        return 1_000_000 if outcome.winner == board.turn else -1_000_000

    us = board.turn
    them = not us

    # --- Own burden (lower = better for us) ---
    own_burden = sum(
        _BURDEN.get(pt, 30)
        for pt in chess.PIECE_TYPES
        for _ in board.pieces(pt, us)
    )

    # --- Opponent burden (higher opponent burden = slightly better for us,
    #     they have more to shed but that's their problem not ours) ---
    opp_burden = sum(
        _BURDEN.get(pt, 30)
        for pt in chess.PIECE_TYPES
        for _ in board.pieces(pt, them)
    )

    # --- Piece counts ---
    own_count = bin(board.occupied_co[us]).count('1')
    opp_count = bin(board.occupied_co[them]).count('1')

    # --- Mobility (number of legal moves available to us) ---
    # More mobility = more control over the sacrifice sequence
    mobility = len(list(board.legal_moves))

    # --- Stalemate bonus: if we're nearly stuck, that could be a win ---
    # Stalemate is a win for the stalemated player in most rulesets
    stalemate_proximity = max(0, 5 - mobility) * 50 if own_count <= 3 else 0

    # --- Pawn advancement bonus (Watkins: pawns are key to breaking endgames) ---
    pawn_advance_bonus = 0
    for sq in board.pieces(chess.PAWN, us):
        rank = chess.square_rank(sq)
        # White wants rank 7 (promotion), black wants rank 0
        dist_to_promo = (7 - rank) if us == chess.WHITE else rank
        pawn_advance_bonus += (6 - dist_to_promo) * 3  # reward proximity to promotion

    # --- Score: we want low own_burden, don't care much about opp_burden ---
    # Primary: minimize own burden (negative own_burden contributes positively)
    # Secondary: mobility (small positive weight)
    # Tertiary: pawn advancement and stalemate proximity
    score = (
        -own_burden * 3          # main driver: shed our pieces
        + opp_burden * 1         # mild: opponent keeping pieces is slightly ok
        - own_count * 15         # having fewer pieces is directly better
        + opp_count * 5          # opponent having more is mildly neutral
        + mobility * 2           # more choices = more control
        + pawn_advance_bonus
        + stalemate_proximity
    )

    return score


def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    """Reorder moves to improve alpha-beta cutoffs.

    Args:
        board: chess.variant.AntichessBoard — current position; used to
            classify moves, look up piece burdens, and detect attacked squares.
        moves: list[chess.Move] — filtered legal moves to reorder.

    Returns:
        list[chess.Move] — same moves sorted by descending move_score.
        Captures score 2000+ (base) plus own-piece burden × 10 minus
        opponent-piece burden × 5.  Non-capture pawn advances and moves to
        opponent-attacked squares receive smaller bonuses.

    Priority (highest first):
    1. Captures that sacrifice our highest-burden pieces
       (bishop > rook > knight > pawn > queen > king)
    2. Among captures, prefer capturing opponent's low-burden pieces
       (forces them to keep their heavy pieces longer)
    3. Non-capture pawn advances toward promotion
    4. Other non-captures that expose pieces (moves to attacked squares)
    5. Everything else

    Antichess:
        Capture scoring is own-attacker-burden minus opponent-victim-burden:
        we want to sacrifice our heaviest pieces (high burden) while capturing
        the opponent's lightest pieces so they retain their heavy pieces as
        their own problem to shed.
    """
    us = board.turn

    def move_score(move: chess.Move) -> int:
        score = 0
        moving_pt = board.piece_type_at(move.from_square)
        captured_pt = board.piece_type_at(move.to_square)

        if captured_pt is not None:
            # It's a capture — we're shedding our piece (moving_pt)
            # and eliminating opponent's piece (captured_pt)
            # We want to sacrifice our high-burden pieces
            our_burden = _BURDEN.get(moving_pt or chess.PAWN, 30)
            # We want opponent to keep high-burden pieces, so prefer capturing low-burden
            their_burden = _BURDEN.get(captured_pt, 30)
            score += 2000 + our_burden * 10 - their_burden * 5

            # Promotion via capture is excellent
            if move.promotion:
                score += 500

        else:
            # Non-capture move
            # Bonus for pawn moves toward promotion
            if moving_pt == chess.PAWN:
                rank = chess.square_rank(move.to_square)
                dist_to_promo = (7 - rank) if us == chess.WHITE else rank
                score += (6 - dist_to_promo) * 20

            # Bonus for moving to squares attacked by opponent
            # (exposes piece for capture next move — we want to lose pieces)
            if board.is_attacked_by(not us, move.to_square):
                our_burden = _BURDEN.get(moving_pt or chess.PAWN, 30)
                score += our_burden * 5

            # Bonus for moving high-burden pieces into danger
            our_burden = _BURDEN.get(moving_pt or chess.PAWN, 30)
            score += our_burden

        return score

    return sorted(moves, key=move_score, reverse=True)
