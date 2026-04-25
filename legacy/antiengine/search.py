"""
Negamax alpha-beta search core with iterative deepening (Person 2).

Features to implement:
- Fail-soft alpha-beta (document vs fail-hard choice).
- Mate / win / loss terminal scores scaled by ply for shortest win preference.
- Node counter; optional split: nodes, qnodes.
- Principal variation extraction (from TT + PV array).
- Iterative deepening: depth 1..N until movetime or stop; keep last completed best move.
- Move ordering:
  - TT best move first
  - Forced captures naturally narrow branch factor
  - MVV-LVA or antichess-specific ordering (sacrifice high value to force opponent takes)
  - History heuristic (from-square, to-square)
  - Killer moves (two slots per ply)
- Quiescence: in antichess extend capture-only chains while captures forced; do not
  evaluate "quiet" when side to move still has unresolved mandatory captures (see eval notes).
- Diagnostics callback or return SearchResult with depth, score, nodes, nps, pv.

Pruning caution (antichess):
- Defer null-move, LMR, futility, razoring until baseline is stable; zugzwang-heavy variant.

Integration:
- Takes EngineState or read-only board + move push/pop stack.
- Uses Evaluator from eval.py (or types.Evaluator protocol).
- Uses TranspositionTable from tt.py.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

import chess

from legacy.antiengine.constants import INFINITY, MATE_VALUE
from legacy.antiengine.tt import EXACT, LOWER_BOUND, UPPER_BOUND
from legacy.antiengine.types import SearchConfig, SearchResult


def _terminal_score(board: chess.Board, ply: int) -> int:
    outcome = board.outcome(claim_draw=True)
    if outcome is None or outcome.winner is None:
        return 0
    if outcome.winner == board.turn:
        return MATE_VALUE - ply
    return -MATE_VALUE + ply


def _key_for_board(board: chess.Board) -> int:
    if hasattr(board, "_transposition_key"):
        return hash(board._transposition_key())
    return hash(board.fen())


def _move_priority(board: chess.Board, move: chess.Move, history: list[list[int]]) -> int:
    score = history[move.from_square][move.to_square]
    if board.is_capture(move):
        captured = board.piece_at(move.to_square)
        mover = board.piece_at(move.from_square)
        if mover is not None:
            score += 10_000 + 10 * mover.piece_type
        if captured is not None:
            score += captured.piece_type
    return score


def _ordered_moves(
    board: chess.Board,
    tt_move: chess.Move | None,
    killers: list[list[str]],
    history: list[list[int]],
    ply: int,
) -> list[chess.Move]:
    legal = list(board.legal_moves)
    if not legal:
        return legal

    ordered: list[chess.Move] = []
    if tt_move in legal:
        ordered.append(tt_move)

    killer_uci = set(killers[min(ply, len(killers) - 1)])
    killer_moves = [m for m in legal if m.uci() in killer_uci and m not in ordered]
    tactical = [m for m in legal if board.is_capture(m) and m not in ordered]
    quiet = [m for m in legal if not board.is_capture(m) and m not in ordered and m not in killer_moves]

    tactical.sort(key=lambda move: _move_priority(board, move, history), reverse=True)
    quiet.sort(key=lambda move: _move_priority(board, move, history), reverse=True)
    ordered.extend(killer_moves)
    ordered.extend(tactical)
    ordered.extend(quiet)
    return ordered


@dataclass(slots=True)
class SearchContext:
    config: SearchConfig
    stop_requested: Callable[[], bool]
    start_time: float = field(default_factory=time.perf_counter)
    deadline: float | None = None
    nodes: int = 0
    stopped: bool = False
    killers: list[list[str]] = field(default_factory=lambda: [[] for _ in range(128)])
    history: list[list[int]] = field(default_factory=lambda: [[0] * 64 for _ in range(64)])

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


def negamax_root(
    board,
    *,
    depth: int,
    alpha: int,
    beta: int,
    tt,
    evaluator,
    config,
    context: SearchContext,
) -> Any:
    """
    Root negamax: iterate legal moves, return best score and best move for this depth.
    """
    alpha_orig = alpha
    best_score = -INFINITY
    best_move = None
    best_line: list[str] = []

    tt_entry = tt.probe_exact_key(_key_for_board(board))
    tt_move = None
    if tt_entry is not None and tt_entry.best_move_uci is not None:
        try:
            tt_move = chess.Move.from_uci(tt_entry.best_move_uci)
        except ValueError:
            tt_move = None

    for move in _ordered_moves(board, tt_move, context.killers, context.history, ply=0):
        if context.should_stop():
            break
        board.push(move)
        score = -negamax(
            board,
            depth - 1,
            -beta,
            -alpha,
            1,
            tt,
            evaluator,
            context.killers,
            context.history,
            config,
            context,
        )
        board.pop()

        if score > best_score:
            best_score = score
            best_move = move
            best_line = [move.uci()]
        if score > alpha:
            alpha = score
        if alpha >= beta:
            break

    if best_move is None:
        legal = list(board.legal_moves)
        if legal:
            best_move = legal[0]
            best_score = alpha_orig
            best_line = [best_move.uci()]
        else:
            best_score = _terminal_score(board, 0)

    flag = EXACT
    if best_score <= alpha_orig:
        flag = UPPER_BOUND
    elif best_score >= beta:
        flag = LOWER_BOUND
    tt.store(_key_for_board(board), depth, best_score, flag, best_move)
    return best_score, best_move, best_line


def negamax(
    board,
    depth: int,
    alpha: int,
    beta: int,
    ply: int,
    tt,
    evaluator,
    killers,
    history,
    config,
    context: SearchContext,
) -> int:
    """Recursive negamax with alpha-beta; updates killers/history side effects."""
    if context.should_stop():
        return alpha

    context.nodes += 1
    alpha_orig = alpha

    if board.is_game_over(claim_draw=True):
        return _terminal_score(board, ply)

    if depth <= 0:
        return quiescence(board, alpha, beta, ply, tt, evaluator, config, context=context, qdepth=0)

    key = _key_for_board(board)
    entry = tt.probe(key, depth)
    if entry is not None:
        if entry.flag == EXACT:
            return entry.score
        if entry.flag == LOWER_BOUND:
            alpha = max(alpha, entry.score)
        elif entry.flag == UPPER_BOUND:
            beta = min(beta, entry.score)
        if alpha >= beta:
            return entry.score

    tt_move = None
    if entry is not None and entry.best_move_uci is not None:
        try:
            tt_move = chess.Move.from_uci(entry.best_move_uci)
        except ValueError:
            tt_move = None

    best_score = -INFINITY
    best_move = None
    for move in _ordered_moves(board, tt_move, killers, history, ply):
        board.push(move)
        score = -negamax(
            board,
            depth - 1,
            -beta,
            -alpha,
            ply + 1,
            tt,
            evaluator,
            killers,
            history,
            config,
            context,
        )
        board.pop()

        if context.should_stop():
            return score

        if score > best_score:
            best_score = score
            best_move = move
        if score > alpha:
            alpha = score
        if alpha >= beta:
            if not board.is_capture(move):
                slots = killers[min(ply, len(killers) - 1)]
                move_uci = move.uci()
                if move_uci not in slots:
                    if len(slots) >= 2:
                        slots.pop()
                    slots.insert(0, move_uci)
            break

    if best_move is None:
        return _terminal_score(board, ply)

    history[best_move.from_square][best_move.to_square] += depth * depth
    flag = EXACT
    if best_score <= alpha_orig:
        flag = UPPER_BOUND
    elif best_score >= beta:
        flag = LOWER_BOUND
    tt.store(key, depth, best_score, flag, best_move)
    return best_score


def quiescence(
    board,
    alpha: int,
    beta: int,
    ply: int,
    tt,
    evaluator,
    config,
    *,
    context: SearchContext,
    qdepth: int,
) -> int:
    """Capture-forced extension until quiet antichess leaf rules."""
    if context.should_stop():
        return alpha
    context.nodes += 1

    if board.is_game_over(claim_draw=True):
        return _terminal_score(board, ply)

    stand_pat = evaluator.evaluate(board, ply=ply)
    if stand_pat >= beta:
        return stand_pat
    if stand_pat > alpha:
        alpha = stand_pat

    if qdepth >= config.qsearch_max_depth:
        return stand_pat

    capture_moves = [move for move in board.legal_moves if board.is_capture(move)]
    if not capture_moves:
        return stand_pat

    for move in capture_moves:
        board.push(move)
        score = -quiescence(
            board,
            -beta,
            -alpha,
            ply + 1,
            tt,
            evaluator,
            config,
            context=context,
            qdepth=qdepth + 1,
        )
        board.pop()
        if score >= beta:
            return score
        if score > alpha:
            alpha = score
    return alpha


def iterative_deepening(
    board,
    *,
    config,
    tt,
    evaluator,
    stop_requested: Callable[[], bool] | None = None,
    info_callback: Callable[[dict[str, Any]], None] | None = None,
) -> Any:
    """
    Loop depth 1..max until time/stop; return SearchResult with best completed line.
    """
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

        score, move, pv = negamax_root(
            board,
            depth=depth,
            alpha=-INFINITY,
            beta=INFINITY,
            tt=tt,
            evaluator=evaluator,
            config=config,
            context=context,
        )
        if context.should_stop():
            break
        if move is not None:
            best_move = move
            best_score = score
            best_depth = depth
            best_pv = pv

        elapsed_ms = max(1.0, (time.perf_counter() - context.start_time) * 1000.0)
        nps = int(context.nodes * 1000.0 / elapsed_ms)
        if info_callback is not None:
            info_callback(
                {
                    "depth": depth,
                    "score_cp": score,
                    "nodes": context.nodes,
                    "time_ms": int(elapsed_ms),
                    "nps": nps,
                    "pv_uci": pv,
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
