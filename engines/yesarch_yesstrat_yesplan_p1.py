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
    # AntichessBoard.legal_moves already enforces mandatory captures:
    # returns captures-only when any capture is available.
    return list(board.legal_moves)


def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    """Score the position for the side to move. Higher = better.

    Antichess inversion: own material is a liability, opponent attacks on our
    pieces are welcome (they'll be forced to capture us).
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
    """Order moves: chain-reaction captures first, then MVA, then promotions.

    Chain reaction bonus (1500): our piece lands on an opponent-attacked square,
    so they must immediately recapture us — two pieces leave the board for one move.
    MVA (Most Valuable Attacker × 2): use our queen/rook first to get them off board.
    Promotion bonus (400 + piece value): promotions create new forced-capture targets.
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
