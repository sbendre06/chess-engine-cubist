from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

import chess

from legacy.classicalengine.constants import INFINITY
from legacy.classicalengine.tt import EXACT, LOWER_BOUND, UPPER_BOUND
from legacy.classicalengine.types import SearchConfig, SearchResult


@dataclass(slots=True)
class SearchContext:
    config: SearchConfig
    stop_requested: Callable[[], bool]
    start_time: float = field(default_factory=time.perf_counter)
    deadline: float | None = None
    nodes: int = 0
    stopped: bool = False
    killers: list[list[str]] = field(default_factory=lambda: [[] for _ in range(128)])

    def __post_init__(self) -> None:
        if self.config.movetime_ms is not None:
            self.deadline = self.start_time + (self.config.movetime_ms / 1000.0)

    def should_stop(self) -> bool:
        if self.stopped:
            return True
        if self.stop_requested():
            self.stopped = True
            return True
        if self.deadline is not None and time.perf_counter() >= self.deadline:
            self.stopped = True
            return True
        if self.config.nodes_limit is not None and self.nodes >= self.config.nodes_limit:
            self.stopped = True
            return True
        return False


def _sanitize_score(score: int, board: chess.Board, model, *, ply: int) -> int:
    if score >= INFINITY or score <= -INFINITY:
        return model.evaluate_board(board, ply=ply)
    return score


def _negamax(
    board: chess.Board,
    *,
    model,
    tt,
    context: SearchContext,
    depth: int,
    alpha: int,
    beta: int,
    ply: int,
) -> int:
    if context.should_stop():
        return alpha
    context.nodes += 1
    alpha_orig = alpha

    if board.is_game_over(claim_draw=True):
        return model.terminal_score(board, ply)

    if depth <= 0:
        return model.evaluate_board(board, ply=ply)

    key = model.board_key(board)
    tt_entry = tt.probe(key, depth)
    if tt_entry is not None:
        if tt_entry.flag == EXACT:
            return tt_entry.score
        if tt_entry.flag == LOWER_BOUND:
            alpha = max(alpha, tt_entry.score)
        elif tt_entry.flag == UPPER_BOUND:
            beta = min(beta, tt_entry.score)
        if alpha >= beta:
            return tt_entry.score

    tt_move = None
    if tt_entry is not None and tt_entry.best_move_uci is not None:
        try:
            tt_move = chess.Move.from_uci(tt_entry.best_move_uci)
        except ValueError:
            tt_move = None

    killer_moves = context.killers[min(ply, len(context.killers) - 1)]
    moves = model.order_moves(board, model.get_legal_moves(board), tt_move=tt_move, killers=killer_moves)

    best_score = -INFINITY
    best_move = None
    for move in moves:
        model.make_move(board, move)
        score = -_negamax(
            board,
            model=model,
            tt=tt,
            context=context,
            depth=depth - 1,
            alpha=-beta,
            beta=-alpha,
            ply=ply + 1,
        )
        model.unmake_move(board)
        score = _sanitize_score(score, board, model, ply=ply)

        if score > best_score:
            best_score = score
            best_move = move
        if score > alpha:
            alpha = score
        if alpha >= beta:
            if not board.is_capture(move):
                slots = context.killers[min(ply, len(context.killers) - 1)]
                move_uci = move.uci()
                if move_uci not in slots:
                    if len(slots) >= 2:
                        slots.pop()
                    slots.insert(0, move_uci)
            break

    if best_move is None:
        return model.terminal_score(board, ply)

    flag = EXACT
    if best_score <= alpha_orig:
        flag = UPPER_BOUND
    elif best_score >= beta:
        flag = LOWER_BOUND
    tt.store(key, depth, best_score, flag, best_move)
    return best_score


def iterative_deepening(
    board: chess.Board,
    *,
    model,
    config: SearchConfig,
    tt,
    stop_requested: Callable[[], bool] | None = None,
    info_callback: Callable[[dict[str, Any]], None] | None = None,
) -> SearchResult:
    stop_requested = stop_requested or (lambda: False)
    context = SearchContext(config=config, stop_requested=stop_requested)

    best_move = None
    best_score = 0
    best_depth = 0
    best_pv: list[str] = []

    max_depth = config.max_depth if not config.infinite else 128
    for depth in range(1, max_depth + 1):
        if context.should_stop():
            break

        legal = model.get_legal_moves(board)
        if not legal:
            break

        alpha = -INFINITY
        local_best_score = -INFINITY
        local_best_move = None
        moves = model.order_moves(board, legal)
        for move in moves:
            model.make_move(board, move)
            score = -_negamax(
                board,
                model=model,
                tt=tt,
                context=context,
                depth=depth - 1,
                alpha=-INFINITY,
                beta=INFINITY,
                ply=1,
            )
            model.unmake_move(board)
            score = _sanitize_score(score, board, model, ply=1)
            if score > local_best_score:
                local_best_score = score
                local_best_move = move

        if local_best_move is not None:
            best_move = local_best_move
            best_score = local_best_score
            best_depth = depth
            best_pv = [best_move.uci()]

        elapsed_ms = max(1.0, (time.perf_counter() - context.start_time) * 1000.0)
        nps = int(context.nodes * 1000.0 / elapsed_ms)
        if info_callback is not None:
            info_callback(
                {
                    "depth": depth,
                    "score_cp": best_score,
                    "nodes": context.nodes,
                    "time_ms": int(elapsed_ms),
                    "nps": nps,
                    "pv_uci": best_pv,
                }
            )

    elapsed_ms = max(1.0, (time.perf_counter() - context.start_time) * 1000.0)
    nps = int(context.nodes * 1000.0 / elapsed_ms)
    return SearchResult(
        depth_completed=best_depth,
        best_move_uci=best_move.uci() if best_move is not None else None,
        score_cp=best_score,
        pv_uci=best_pv,
        nodes=context.nodes,
        elapsed_ms=elapsed_ms,
        nps=nps,
        stopped=context.stopped,
    )
