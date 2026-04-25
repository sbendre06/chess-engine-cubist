"""Frozen harness: UCI loop + search, parametrized on a loaded engine module.

The engine module is any object exposing the Core 3 callables:
    get_pseudo_legal_moves(board)
    evaluate_board(board)
    order_moves(board, moves)

Only these three are invoked from the search. Everything else (terminal
scoring, legal-move filtering, time control, UCI) is owned by the harness.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field, replace
from types import ModuleType
from typing import Any, Callable

import chess
import chess.variant

from harness.logger import ExperimentLogger


ENGINE_NAME = "Cubist Frozen Harness"
ENGINE_AUTHOR = "Cubist Ablation Team"
MATE_SCORE = 1_000_000
INFINITY = 10_000_000


@dataclass(slots=True)
class SearchConfig:
    max_depth: int = 4
    movetime_ms: int | None = None
    infinite: bool = False
    nodes_limit: int | None = None
    wtime_ms: int | None = None
    btime_ms: int | None = None
    winc_ms: int = 0
    binc_ms: int = 0
    movestogo: int | None = None


@dataclass(slots=True)
class SearchResult:
    depth_completed: int
    best_move_uci: str | None
    score_cp: int
    pv_uci: list[str]
    nodes: int
    elapsed_ms: int
    nps: int
    stopped: bool


@dataclass(slots=True)
class SearchContext:
    config: SearchConfig
    stop_requested: Callable[[], bool]
    start_time: float = field(default_factory=time.perf_counter)
    deadline: float | None = None
    nodes: int = 0
    stopped: bool = False

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


def _parse_optional_int(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _terminal_score(board: chess.variant.AntichessBoard, ply: int) -> int:
    outcome = board.outcome(claim_draw=True)
    if outcome is None or outcome.winner is None:
        return 0
    return (MATE_SCORE - ply) if outcome.winner == board.turn else (-MATE_SCORE + ply)


def _legal_from_engine(
    board: chess.variant.AntichessBoard,
    engine: ModuleType,
) -> list[chess.Move]:
    """Ask engine for pseudo-legals, then filter through board.legal_moves.

    Safety net: even if an engine implementation lets illegal moves through,
    the harness never plays an illegal move.
    """
    legal_set = set(board.legal_moves)
    candidates = engine.get_pseudo_legal_moves(board)
    return [m for m in candidates if m in legal_set]


def _ordered_moves(
    board: chess.variant.AntichessBoard,
    engine: ModuleType,
) -> list[chess.Move]:
    legal = _legal_from_engine(board, engine)
    ordered = engine.order_moves(board, legal)
    legal_set = set(legal)
    return [m for m in ordered if m in legal_set]


def _negamax(
    board: chess.variant.AntichessBoard,
    engine: ModuleType,
    depth: int,
    alpha: int,
    beta: int,
    context: SearchContext,
    ply: int,
) -> int:
    if context.should_stop():
        return engine.evaluate_board(board)

    context.nodes += 1
    if board.is_game_over(claim_draw=True):
        return _terminal_score(board, ply)
    if depth <= 0:
        return engine.evaluate_board(board)

    moves = _ordered_moves(board, engine)
    if not moves:
        return _terminal_score(board, ply)

    best_score = -INFINITY
    for move in moves:
        board.push(move)
        score = -_negamax(board, engine, depth - 1, -beta, -alpha, context, ply + 1)
        board.pop()

        if score > best_score:
            best_score = score
        if score > alpha:
            alpha = score
        if alpha >= beta or context.should_stop():
            break

    return best_score if best_score != -INFINITY else engine.evaluate_board(board)


def iterative_deepening(
    board: chess.variant.AntichessBoard,
    engine: ModuleType,
    config: SearchConfig,
    *,
    stop_requested: Callable[[], bool] | None = None,
    info_callback: Callable[[dict[str, Any]], None] | None = None,
) -> SearchResult:
    stop_requested = stop_requested or (lambda: False)
    context = SearchContext(config=config, stop_requested=stop_requested)

    root_moves = _ordered_moves(board, engine)
    if not root_moves:
        elapsed_ms = max(1, int((time.perf_counter() - context.start_time) * 1000.0))
        return SearchResult(
            depth_completed=0,
            best_move_uci=None,
            score_cp=_terminal_score(board, 0),
            pv_uci=[],
            nodes=context.nodes,
            elapsed_ms=elapsed_ms,
            nps=0,
            stopped=context.stopped,
        )

    best_move = root_moves[0]
    best_score = engine.evaluate_board(board)
    best_depth = 0

    max_depth = 128 if config.infinite else max(1, config.max_depth)
    for depth in range(1, max_depth + 1):
        if context.should_stop():
            break

        local_best_move: chess.Move | None = None
        local_best_score = -INFINITY
        depth_completed = True
        current_root_moves = _ordered_moves(board, engine)

        for move in current_root_moves:
            if context.should_stop():
                depth_completed = False
                break

            board.push(move)
            score = -_negamax(board, engine, depth - 1, -INFINITY, INFINITY, context, 1)
            board.pop()

            if score > local_best_score:
                local_best_score = score
                local_best_move = move

        if local_best_move is not None and (depth_completed or best_depth == 0):
            best_move = local_best_move
            best_score = local_best_score
            best_depth = depth if depth_completed else best_depth

        elapsed_ms = max(1, int((time.perf_counter() - context.start_time) * 1000.0))
        nps = int(context.nodes * 1000.0 / elapsed_ms)
        if info_callback is not None and local_best_move is not None:
            info_callback(
                {
                    "depth": depth if depth_completed else max(best_depth, 1),
                    "score_cp": best_score if best_depth else local_best_score,
                    "nodes": context.nodes,
                    "time_ms": elapsed_ms,
                    "nps": nps,
                    "pv_uci": [local_best_move.uci()],
                }
            )

        if not depth_completed:
            break

    elapsed_ms = max(1, int((time.perf_counter() - context.start_time) * 1000.0))
    nps = int(context.nodes * 1000.0 / elapsed_ms)
    return SearchResult(
        depth_completed=best_depth,
        best_move_uci=best_move.uci(),
        score_cp=best_score,
        pv_uci=[best_move.uci()],
        nodes=context.nodes,
        elapsed_ms=elapsed_ms,
        nps=nps,
        stopped=context.stopped,
    )


class FrozenUCIEngine:
    """UCI shell. Owns stdin/stdout, delegates move choice to the loaded engine."""

    def __init__(self, engine_module: ModuleType, engine_name: str) -> None:
        self.engine_module = engine_module
        self.engine_name_for_id = f"{ENGINE_NAME} [{engine_name}]"
        self.board = chess.variant.AntichessBoard()
        self.base_config = SearchConfig()
        self.logger = ExperimentLogger(engine_name=engine_name)
        self._quit_requested = False
        self._search_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._io_lock = threading.Lock()

    @property
    def quit_requested(self) -> bool:
        return self._quit_requested

    def handle_command(self, line: str) -> None:
        if not line:
            return

        parts = line.strip().split()
        command = parts[0]
        args = parts[1:]

        if command == "uci":
            self._send(f"id name {self.engine_name_for_id}")
            self._send(f"id author {ENGINE_AUTHOR}")
            self._send("option name UCI_Variant type combo default antichess var antichess")
            self._send("option name Hash type spin default 64 min 1 max 4096")
            self._send("uciok")
            return

        if command == "isready":
            self._send("readyok")
            return

        if command == "ucinewgame":
            self.stop_search()
            self.board.reset()
            return

        if command == "setoption":
            # No agent-settable options in the frozen build; ignore silently.
            return

        if command == "position":
            self.stop_search()
            try:
                self._handle_position(args)
            except ValueError as exc:
                self._send(f"info string {exc}")
            return

        if command == "go":
            self.go(self._parse_go(args))
            return

        if command == "stop":
            self.stop_search()
            return

        if command == "quit":
            self.stop_search()
            self._quit_requested = True

    def go(self, config: SearchConfig) -> None:
        self.stop_search()
        self._stop_event.clear()
        config = self._resolve_time_budget(config)
        search_board = self.board.copy(stack=True)
        fen = search_board.fen()
        turn = "white" if search_board.turn == chess.WHITE else "black"

        def on_info(payload: dict[str, Any]) -> None:
            pv = " ".join(payload["pv_uci"])
            self._send(
                "info"
                f" depth {payload['depth']}"
                f" score cp {payload['score_cp']}"
                f" nodes {payload['nodes']}"
                f" nps {payload['nps']}"
                f" time {payload['time_ms']}"
                f"{' pv ' + pv if pv else ''}"
            )

        def run_search() -> None:
            result = iterative_deepening(
                search_board,
                self.engine_module,
                config,
                stop_requested=self._stop_event.is_set,
                info_callback=on_info,
            )
            bestmove = result.best_move_uci
            if bestmove is None:
                fallback = _ordered_moves(search_board, self.engine_module)
                bestmove = fallback[0].uci() if fallback else "0000"
            self.logger.log_search(fen=fen, turn=turn, result=result, bestmove=bestmove)
            self._send(f"bestmove {bestmove}")

        self._search_thread = threading.Thread(target=run_search, daemon=True)
        self._search_thread.start()

    def stop_search(self) -> None:
        if self._search_thread is None:
            return
        if self._search_thread.is_alive():
            self._stop_event.set()
            self._search_thread.join(timeout=2.0)
        self._search_thread = None

    def _handle_position(self, args: list[str]) -> None:
        if not args:
            return

        moves_idx = args.index("moves") if "moves" in args else -1
        move_tokens: list[str] = []
        if moves_idx != -1:
            move_tokens = args[moves_idx + 1 :]
            pos_tokens = args[:moves_idx]
        else:
            pos_tokens = args

        if pos_tokens and pos_tokens[0] == "startpos":
            self.board.reset()
        elif pos_tokens and pos_tokens[0] == "fen":
            fen = " ".join(pos_tokens[1:])
            self.board.set_fen(fen)

        for move_uci in move_tokens:
            move = chess.Move.from_uci(move_uci)
            if move not in self.board.legal_moves:
                raise ValueError(f"Illegal move in position: {move_uci}")
            self.board.push(move)

    def _parse_go(self, args: list[str]) -> SearchConfig:
        config = replace(self.base_config)
        i = 0
        while i < len(args):
            token = args[i]
            if token == "depth" and i + 1 < len(args):
                try:
                    config.max_depth = max(1, int(args[i + 1]))
                except ValueError:
                    pass
                config.infinite = False
                i += 2
                continue
            if token == "movetime" and i + 1 < len(args):
                try:
                    config.movetime_ms = max(1, int(args[i + 1]))
                except ValueError:
                    pass
                config.infinite = False
                i += 2
                continue
            if token == "nodes" and i + 1 < len(args):
                try:
                    config.nodes_limit = max(1, int(args[i + 1]))
                except ValueError:
                    pass
                i += 2
                continue
            if token == "wtime" and i + 1 < len(args):
                config.wtime_ms = _parse_optional_int(args[i + 1])
                i += 2
                continue
            if token == "btime" and i + 1 < len(args):
                config.btime_ms = _parse_optional_int(args[i + 1])
                i += 2
                continue
            if token == "winc" and i + 1 < len(args):
                config.winc_ms = _parse_optional_int(args[i + 1]) or 0
                i += 2
                continue
            if token == "binc" and i + 1 < len(args):
                config.binc_ms = _parse_optional_int(args[i + 1]) or 0
                i += 2
                continue
            if token == "movestogo" and i + 1 < len(args):
                config.movestogo = _parse_optional_int(args[i + 1])
                i += 2
                continue
            if token == "infinite":
                config.infinite = True
                config.movetime_ms = None
                i += 1
                continue
            i += 1
        return config

    def _resolve_time_budget(self, config: SearchConfig) -> SearchConfig:
        if config.infinite or config.movetime_ms is not None:
            return config

        remaining_ms = config.wtime_ms if self.board.turn == chess.WHITE else config.btime_ms
        increment_ms = config.winc_ms if self.board.turn == chess.WHITE else config.binc_ms
        if remaining_ms is None:
            return config

        moves_to_go = config.movestogo or 20
        share = remaining_ms // max(1, moves_to_go)
        budget = share + (increment_ms // 2)
        config.movetime_ms = max(1, min(remaining_ms, budget))
        return config

    def _send(self, line: str) -> None:
        with self._io_lock:
            print(line, flush=True)
