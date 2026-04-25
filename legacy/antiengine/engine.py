"""
UCIEngine facade: wires EngineState, Search, Eval, TT, optional TB (integrator).

Responsibilities:
- Construct subcomponents from UCI setoption (Hash, SyzygyPath, custom eval weights file).
- Implement types.UCIEngine protocol: handle_command(line) or split parse_uci / dispatch.
- position / go / stop state machine:
  - go: run iterative_deepening in main thread or worker; set abort flag on stop.
- bestmove fallback: if search fails or depth 0, pick random legal move (MVP) then improve.
- Aggregate diagnostics for info string formatting.

Keep this file orchestration-only; no deep alpha-beta here (search.py).
"""

from __future__ import annotations

import threading
from dataclasses import replace

from antiengine.board import EngineState
from antiengine.constants import ENGINE_AUTHOR, ENGINE_NAME, ENGINE_VERSION
from antiengine.eval import AntichessEvaluator
from antiengine.search import iterative_deepening
from antiengine.tt import TranspositionTable
from antiengine.types import SearchConfig

class UCIEngine:
    """Top-level engine object used by uci.py."""

    def __init__(self) -> None:
        """Create board wrapper, TT, evaluator, search config defaults."""
        self.state = EngineState()
        self.tt = TranspositionTable(megabytes=64)
        self.evaluator = AntichessEvaluator()
        self.base_config = SearchConfig()
        self.syzygy_path = ""
        self._quit_requested = False
        self._search_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._io_lock = threading.Lock()

    def handle_command(self, line: str) -> None:
        """Parse one UCI line and update state or launch search (types.UCIEngine)."""
        if not line:
            return

        parts = line.strip().split()
        command = parts[0]
        args = parts[1:]

        if command == "uci":
            self._send(f"id name {ENGINE_NAME} {ENGINE_VERSION}")
            self._send(f"id author {ENGINE_AUTHOR}")
            self._send("option name UCI_Variant type combo default antichess var antichess")
            self._send("option name Hash type spin default 64 min 1 max 4096")
            self._send("option name SyzygyPath type string default")
            self._send("uciok")
            return

        if command == "isready":
            self._send("readyok")
            return

        if command == "ucinewgame":
            self.stop_search()
            self.state.reset_startpos()
            self.tt.clear()
            return

        if command == "setoption":
            self._handle_setoption(args)
            return

        if command == "position":
            self._handle_position(args)
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
            return

    def go(self, search_config) -> None:
        """Start search from current position; emit info + bestmove when done."""
        self.stop_search()
        self._stop_event.clear()
        board = self.state.copy_board()

        def on_info(payload: dict) -> None:
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
                board,
                config=search_config,
                tt=self.tt,
                evaluator=self.evaluator,
                stop_requested=self._stop_event.is_set,
                info_callback=on_info,
            )
            bestmove = result.best_move_uci
            if bestmove is None:
                legal = list(self.state.board.legal_moves)
                bestmove = legal[0].uci() if legal else "0000"
            self._send(f"bestmove {bestmove}")

        self._search_thread = threading.Thread(target=run_search, daemon=True)
        self._search_thread.start()

    def stop_search(self) -> None:
        """Signal search to finish quickly with best move so far."""
        if self._search_thread is None:
            return
        if self._search_thread.is_alive():
            self._stop_event.set()
            self._search_thread.join(timeout=1.0)
        self._search_thread = None

    @property
    def quit_requested(self) -> bool:
        return self._quit_requested

    def _send(self, line: str) -> None:
        with self._io_lock:
            print(line, flush=True)

    def _handle_setoption(self, args: list[str]) -> None:
        if not args:
            return

        normalized = " ".join(args)
        lower = normalized.lower()
        if "name hash" in lower and "value" in lower:
            try:
                value = int(lower.split("value", 1)[1].strip())
            except ValueError:
                return
            self.tt.resize(value)
            return
        if "name syzygypath" in lower:
            value = ""
            if "value" in lower:
                value = normalized[lower.index("value") + len("value") :].strip()
            self.syzygy_path = value

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
            self.state.reset_startpos()
        elif pos_tokens and pos_tokens[0] == "fen":
            fen = " ".join(pos_tokens[1:])
            self.state.set_fen(fen)

        if move_tokens:
            self.state.play_moves(move_tokens)

    def _parse_go(self, args: list[str]) -> SearchConfig:
        config = replace(self.base_config)
        if not args:
            return config

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
            if token == "infinite":
                config.infinite = True
                config.movetime_ms = None
                i += 1
                continue
            i += 1
        return config
