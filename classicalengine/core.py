from __future__ import annotations

import chess

from classicalengine.constants import MATE_VALUE, PIECE_VALUE


def board_key(board: chess.Board) -> int:
    if hasattr(board, "_transposition_key"):
        return hash(board._transposition_key())
    return hash(board.fen())


def evaluate_board(board: chess.Board, evaluator, *, ply: int = 0) -> int:
    return evaluator.evaluate(board, ply=ply)


def get_legal_moves(board: chess.Board) -> list[chess.Move]:
    return list(board.legal_moves)


def get_pseudo_legal_moves(board: chess.Board) -> list[chess.Move]:
    return list(board.pseudo_legal_moves)


def make_move(board: chess.Board, move: chess.Move) -> None:
    board.push(move)


def unmake_move(board: chess.Board) -> chess.Move:
    return board.pop()


def terminal_score(board: chess.Board, ply: int) -> int:
    if board.is_checkmate():
        return -MATE_VALUE + ply
    if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
        return 0
    outcome = board.outcome(claim_draw=True)
    if outcome is None or outcome.winner is None:
        return 0
    return (MATE_VALUE - ply) if outcome.winner == board.turn else (-MATE_VALUE + ply)


def mvv_lva_score(board: chess.Board, move: chess.Move) -> int:
    if not board.is_capture(move):
        return 0
    captured = board.piece_at(move.to_square)
    attacker = board.piece_at(move.from_square)
    captured_val = PIECE_VALUE.get(captured.piece_type, 0) if captured else 0
    attacker_val = PIECE_VALUE.get(attacker.piece_type, 1) if attacker else 1
    return 10_000 + captured_val * 10 - attacker_val
