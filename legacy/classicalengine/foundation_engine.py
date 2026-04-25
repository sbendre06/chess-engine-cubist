from __future__ import annotations

import threading
from dataclasses import replace

from classicalengine.board import EngineState
from classicalengine.constants import ENGINE_AUTHOR
from classicalengine.foundation_model import FoundationModel
from classicalengine.foundation_search import iterative_deepening
from classicalengine.tt import TranspositionTable
from classicalengine.types import SearchConfig


class FoundationUCIEngine:
    """Minimal UCI engine wired to FoundationModel for easy experimentation."""

    def __init__(self) -> None:
        self.state = EngineState()
        self.model = FoundationModel()
        self.tt = TranspositionTable(megabytes=64)
        self.base_config = SearchConfig(max_depth=4)
        self._quit_requested = False
        self._search_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._io_lock = threading.Lock()

    def handle_command(self, line: str) -> None:
        if not line:
            return
        parts = line.strip().split()
        command = parts[0]
        args = parts[1:]

        if command == "uci":
            self._send("id name Cubist Foundation Classical")
            self._send(f"id author {ENGINE_AUTHOR}")
            self._send("option name Hash type spin default 64 min 1 max 4096")
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

    def go(self, config: SearchConfig) -> None:
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
                model=self.model,
                config=config,
                tt=self.tt,
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
        normalized = " ".join(args).lower()
        if "name hash" in normalized and "value" in normalized:
            try:
                value = int(normalized.split("value", 1)[1].strip())
            except ValueError:
                return
            self.tt.resize(value)

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
        i = 0
        while i < len(args):
            token = args[i]
            if token == "depth" and i + 1 < len(args):
                try:
                    config.max_depth = max(1, int(args[i + 1]))
                except ValueError:
                    pass
                i += 2
                continue
            if token == "movetime" and i + 1 < len(args):
                try:
                    config.movetime_ms = max(1, int(args[i + 1]))
                except ValueError:
                    pass
                i += 2
                continue
            i += 1
        return config
