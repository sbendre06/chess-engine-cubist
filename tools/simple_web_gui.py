#!/usr/bin/env python3
"""
Very simple browser GUI for playing antichess vs any engines/<name>.py.

Run:
  .venv/bin/python tools/simple_web_gui.py --engine baseline --you white --depth 3
  .venv/bin/python tools/simple_web_gui.py --engine yesarch_yessttrat_noplan --depth 3

Then open:
  http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import chess
import chess.variant

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.engine import SearchConfig, iterative_deepening
from harness.loader import EngineContractError, load_engine

UNICODE_PIECE = {
    "P": "♙",
    "N": "♘",
    "B": "♗",
    "R": "♖",
    "Q": "♕",
    "K": "♔",
    "p": "♟",
    "n": "♞",
    "b": "♝",
    "r": "♜",
    "q": "♛",
    "k": "♚",
}


HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Cubist AntiChess</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 20px; }
    #board { display: grid; grid-template-columns: repeat(8, 56px); width: 448px; border: 1px solid #333; }
    .sq { width: 56px; height: 56px; border: none; font-size: 34px; cursor: pointer; }
    .light { background: #f0d9b5; }
    .dark { background: #b58863; }
    .selected { outline: 3px solid #f6e27f; }
    .target { outline: 3px solid #8bd17c; }
    #status { margin: 12px 0; min-height: 24px; }
    #controls { margin-top: 12px; }
    button { padding: 8px 12px; margin-right: 8px; }
    .small { color: #666; font-size: 13px; margin-top: 8px; }
  </style>
</head>
<body>
  <h2>Cubist AntiChess</h2>
  <div id="status"></div>
  <div id="board"></div>
  <div id="controls">
    <button id="newGameBtn">New Game</button>
    <button id="refreshBtn">Refresh</button>
  </div>
  <div class="small">Click source square then destination square. Promotions prompt for piece (q/r/b/n/k).</div>

  <script>
    const boardEl = document.getElementById("board");
    const statusEl = document.getElementById("status");
    const newGameBtn = document.getElementById("newGameBtn");
    const refreshBtn = document.getElementById("refreshBtn");

    let current = null;
    let selected = null;

    function indexToSquare(idx) {
      const file = idx % 8;
      const rank = Math.floor(idx / 8);
      return "abcdefgh"[file] + (rank + 1);
    }

    function squareToIndex(sq) {
      const file = "abcdefgh".indexOf(sq[0]);
      const rank = Number(sq[1]) - 1;
      return rank * 8 + file;
    }

    function legalTargetsFrom(selectedSq) {
      if (!current || !current.legal_moves) return new Set();
      const out = new Set();
      for (const uci of current.legal_moves) {
        if (uci.startsWith(selectedSq)) out.add(uci.slice(2, 4));
      }
      return out;
    }

    async function api(path, method = "GET", body = null) {
      const res = await fetch(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : null,
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "Request failed");
      return data;
    }

    function pieceAt(squareName) {
      return current.board[squareToIndex(squareName)];
    }

    async function clickSquare(squareName) {
      if (!current || current.game_over || current.engine_turn) return;

      const piece = pieceAt(squareName);
      if (!selected) {
        if (piece && piece.color === current.turn) {
          selected = squareName;
          render();
        }
        return;
      }

      if (squareName === selected) {
        selected = null;
        render();
        return;
      }

      let base = selected + squareName;
      let candidates = current.legal_moves.filter(m => m.startsWith(base));
      if (candidates.length === 0) {
        selected = piece && piece.color === current.turn ? squareName : null;
        render();
        return;
      }

      let uci = candidates[0];
      if (candidates.length > 1) {
        const choice = prompt("Promotion piece? q/r/b/n/k", "q");
        if (!choice) return;
        uci = base + choice.trim().toLowerCase();
      }

      try {
        await api("/move", "POST", { uci });
        selected = null;
        await loadState();
      } catch (err) {
        statusEl.textContent = String(err.message);
      }
    }

    function render() {
      boardEl.innerHTML = "";
      const targets = selected ? legalTargetsFrom(selected) : new Set();

      for (let rank = 7; rank >= 0; rank--) {
        for (let file = 0; file < 8; file++) {
          const idx = rank * 8 + file;
          const sq = indexToSquare(idx);
          const piece = current.board[idx];
          const isLight = (file + rank) % 2 === 1;
          const btn = document.createElement("button");
          btn.className = "sq " + (isLight ? "light" : "dark");
          if (selected === sq) btn.classList.add("selected");
          if (targets.has(sq)) btn.classList.add("target");
          btn.textContent = piece ? piece.unicode : "";
          btn.onclick = () => clickSquare(sq);
          boardEl.appendChild(btn);
        }
      }

      statusEl.textContent = current.status;
    }

    async function loadState() {
      const data = await api("/state");
      current = data.state;
      if (current.engine_turn && !current.game_over) {
        statusEl.textContent = "Engine thinking...";
        const moved = await api("/engine_move", "POST", {});
        current = moved.state;
      }
      render();
    }

    newGameBtn.onclick = async () => {
      await api("/new_game", "POST", {});
      selected = null;
      await loadState();
    };
    refreshBtn.onclick = () => loadState();

    loadState();
  </script>
</body>
</html>
"""


class GameSession:
    def __init__(self, you_are_white: bool, config: SearchConfig, engine_name: str) -> None:
        self.you_are_white = you_are_white
        self.config = config
        self.engine_name = engine_name
        self.engine_module = load_engine(engine_name)
        self.board = chess.variant.AntichessBoard()
        self.last_engine_info = ""

    def reset(self) -> None:
        self.board.reset()
        self.last_engine_info = ""

    def is_human_turn(self) -> bool:
        turn = self.board.turn
        return (turn == chess.WHITE and self.you_are_white) or (
            turn == chess.BLACK and not self.you_are_white
        )

    def _board_payload(self) -> list[dict[str, str] | None]:
        out: list[dict[str, str] | None] = []
        for sq in range(64):
            piece = self.board.piece_at(sq)
            if piece is None:
                out.append(None)
                continue
            symbol = piece.symbol()
            out.append(
                {
                    "symbol": symbol,
                    "unicode": UNICODE_PIECE[symbol],
                    "color": "white" if piece.color == chess.WHITE else "black",
                }
            )
        return out

    def _status(self) -> str:
        if self.board.is_game_over(claim_draw=True):
            outcome = self.board.outcome(claim_draw=True)
            if outcome is None or outcome.winner is None:
                return "Game over: draw."
            winner = "White" if outcome.winner == chess.WHITE else "Black"
            return f"Game over: {winner} wins (antichess rules)."

        mover = "White" if self.board.turn == chess.WHITE else "Black"
        actor = "You" if self.is_human_turn() else f"Engine: {self.engine_name}"
        suffix = f" | {self.last_engine_info}" if self.last_engine_info else ""
        return f"{mover} to move ({actor}).{suffix}"

    def snapshot(self) -> dict[str, object]:
        board = self.board
        game_over = board.is_game_over(claim_draw=True)
        return {
            "fen": board.fen(),
            "turn": "white" if board.turn == chess.WHITE else "black",
            "board": self._board_payload(),
            "legal_moves": [m.uci() for m in board.legal_moves],
            "game_over": game_over,
            "engine_turn": (not self.is_human_turn()) and (not game_over),
            "status": self._status(),
        }

    def play_human_move(self, move_uci: str) -> None:
        if not self.is_human_turn():
            raise ValueError("It is not your turn.")
        move = chess.Move.from_uci(move_uci)
        if move not in self.board.legal_moves:
            raise ValueError(f"Illegal move: {move_uci}")
        self.board.push(move)

    def play_engine_move(self) -> None:
        if self.is_human_turn() or self.board.is_game_over(claim_draw=True):
            return
        board_copy = self.board.copy(stack=True)
        result = iterative_deepening(board_copy, self.engine_module, self.config)
        move_uci = result.best_move_uci
        legal = list(self.board.legal_moves)
        if not legal:
            return
        if move_uci is None:
            chosen = legal[0]
        else:
            chosen = chess.Move.from_uci(move_uci)
            if chosen not in self.board.legal_moves:
                chosen = legal[0]
        self.board.push(chosen)
        self.last_engine_info = (
            f"engine {chosen.uci()} "
            f"(depth={result.depth_completed}, score={result.score_cp}, "
            f"nodes={result.nodes}, time={int(result.elapsed_ms)}ms)"
        )


def _json(handler: BaseHTTPRequestHandler, code: int, payload: dict[str, object]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, object]:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length > 0 else b"{}"
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def make_handler(session: GameSession):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A003
            return

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/":
                body = HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if self.path == "/state":
                _json(self, 200, {"ok": True, "state": session.snapshot()})
                return

            _json(self, 404, {"ok": False, "error": "Not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/new_game":
                session.reset()
                _json(self, 200, {"ok": True, "state": session.snapshot()})
                return

            if self.path == "/move":
                data = _read_json(self)
                move_uci = str(data.get("uci", "")).strip()
                if not move_uci:
                    _json(self, 400, {"ok": False, "error": "Missing move uci."})
                    return
                try:
                    session.play_human_move(move_uci)
                except ValueError as exc:
                    _json(self, 400, {"ok": False, "error": str(exc)})
                    return
                _json(self, 200, {"ok": True, "state": session.snapshot()})
                return

            if self.path == "/engine_move":
                session.play_engine_move()
                _json(self, 200, {"ok": True, "state": session.snapshot()})
                return

            _json(self, 404, {"ok": False, "error": "Not found"})

    return Handler


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple browser GUI for antichess vs any engines/<name>.py.")
    parser.add_argument("--engine", default="baseline",
                        help="Engine module name under engines/ (e.g. baseline, yesarch_yessttrat_noplan).")
    parser.add_argument("--you", choices=["white", "black"], default="white", help="Your side.")
    parser.add_argument("--depth", type=int, default=3, help="Engine fixed search depth.")
    parser.add_argument("--movetime", type=int, default=None, help="Engine move time in ms.")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = SearchConfig(max_depth=max(1, args.depth))
    if args.movetime is not None and args.movetime > 0:
        config.movetime_ms = args.movetime

    try:
        session = GameSession(
            you_are_white=(args.you == "white"),
            config=config,
            engine_name=args.engine,
        )
    except EngineContractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

    handler = make_handler(session)

    host = "127.0.0.1"
    server = ThreadingHTTPServer((host, args.port), handler)
    print(f"Simple GUI ready at http://{host}:{args.port}  (engine={args.engine})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
