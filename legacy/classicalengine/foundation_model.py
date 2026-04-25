from __future__ import annotations

import chess

from legacy.classicalengine.constants import MATE_VALUE, PIECE_VALUE, PST_BY_PIECE


class FoundationModel:
    """
    Intentionally simple, centralized model for experimentation.

    The point of this class is to be easy to delete/rewrite:
    - Keep all core "chess intelligence" functions in one place.
    - Agents can replace individual methods or the entire class.
    """

    def evaluate_board(self, board: chess.Board, *, ply: int = 0) -> int:
        """Return centipawn-ish score from side-to-move perspective."""
        white = 0
        black = 0
        for square, piece in board.piece_map().items():
            val = PIECE_VALUE[piece.piece_type]
            pst = self._piece_square(piece.piece_type, piece.color, square)
            if piece.color == chess.WHITE:
                white += val + pst
            else:
                black += val + pst

        # Lightweight mobility term.
        own_mobility = board.legal_moves.count()
        probe = board.copy(stack=False)
        probe.turn = not board.turn
        opp_mobility = probe.legal_moves.count()
        mobility = 3 * (own_mobility - opp_mobility)

        score_white = white - black
        return (score_white if board.turn == chess.WHITE else -score_white) + mobility

    def get_legal_moves(self, board: chess.Board) -> list[chess.Move]:
        return list(board.legal_moves)

    def get_pseudo_legal_moves(self, board: chess.Board) -> list[chess.Move]:
        return list(board.pseudo_legal_moves)

    def order_moves(
        self,
        board: chess.Board,
        moves: list[chess.Move],
        *,
        tt_move: chess.Move | None = None,
        killers: list[str] | None = None,
    ) -> list[chess.Move]:
        """Basic ordering: TT move, killers, captures/promotions/checks, then quiet moves."""
        ordered: list[chess.Move] = []
        if tt_move in moves:
            ordered.append(tt_move)

        killer_set = set(killers or [])
        killer_moves = [m for m in moves if m.uci() in killer_set and m not in ordered]
        tactical = [m for m in moves if self._is_tactical(board, m) and m not in ordered]
        quiet = [m for m in moves if m not in ordered and m not in killer_moves and m not in tactical]

        tactical.sort(key=lambda m: self._tactical_score(board, m), reverse=True)
        ordered.extend(killer_moves)
        ordered.extend(tactical)
        ordered.extend(quiet)
        return ordered

    def make_move(self, board: chess.Board, move: chess.Move) -> None:
        board.push(move)

    def unmake_move(self, board: chess.Board) -> chess.Move:
        return board.pop()

    def board_key(self, board: chess.Board) -> int:
        if hasattr(board, "_transposition_key"):
            return hash(board._transposition_key())
        return hash(board.fen())

    def terminal_score(self, board: chess.Board, ply: int) -> int:
        if board.is_checkmate():
            return -MATE_VALUE + ply
        if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
            return 0
        return 0

    def _piece_square(self, piece_type: int, color: chess.Color, square: chess.Square) -> int:
        table = PST_BY_PIECE[piece_type]
        idx = square if color == chess.WHITE else chess.square_mirror(square)
        return table[idx]

    def _is_tactical(self, board: chess.Board, move: chess.Move) -> bool:
        return board.is_capture(move) or move.promotion is not None or board.gives_check(move)

    def _tactical_score(self, board: chess.Board, move: chess.Move) -> int:
        score = 0
        if board.is_capture(move):
            captured = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            cap = PIECE_VALUE.get(captured.piece_type, 0) if captured else 0
            atk = PIECE_VALUE.get(attacker.piece_type, 1) if attacker else 1
            score += 10_000 + cap * 10 - atk
        if move.promotion is not None:
            score += PIECE_VALUE.get(move.promotion, 0)
        if board.gives_check(move):
            score += 50
        return score
