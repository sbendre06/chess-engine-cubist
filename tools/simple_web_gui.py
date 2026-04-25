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

ENGINE_LABELS: dict[str, str] = {
    "baseline":                   "Baseline Bob",
    "caveman":                    "Caveman Dan",
    "noarch_nostrat_noplan":      "Lost Luke",
    "noarch_nostrat_yesplan":     "Plan-mode Patty",
    "noarch_yesstrat_noplan":     "Idea-Guy Ian",
    "yesarch_nostrat_noplan":     "Architectural Alina",
    "yesarch_yessttrat_noplan":   "Supervisor Sarah",
    "yesarch-nostrat-yesplan":    "Methodical Machine Mary",
    "yesarch_yesstrat_yesplan_p1": "Quant Researcher Kevin",
    "arch1-strat1-plan1":         "Omnipotent Owen",
}


def _engine_label(name: str) -> str:
    return ENGINE_LABELS.get(name, name)


def _engines_json() -> str:
    return json.dumps([{"name": k, "label": v} for k, v in ENGINE_LABELS.items()])


UNICODE_PIECE = {
    "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
    "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
}


def _build_html(active_engine: str) -> str:
    return HTML.replace("__ENGINES_JSON__", _engines_json()).replace("__ACTIVE_ENGINE__", active_engine)


HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Antichess - Good Luck!!</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 20px; }
    #layout { display: flex; gap: 28px; align-items: flex-start; }

    /* Board frame */
    #board-wrap { display: flex; align-items: flex-start; gap: 6px; }
    #rank-labels {
      display: flex; flex-direction: column; justify-content: space-around;
      height: 512px; font-size: 12px; color: #888; user-select: none;
      padding-right: 2px;
    }
    #board-col { display: flex; flex-direction: column; gap: 4px; }
    #board {
      display: grid; grid-template-columns: repeat(8, 64px);
      width: 512px;
      box-shadow: 0 6px 24px rgba(0,0,0,0.4);
      border: 2px solid #555;
    }
    #file-labels {
      display: flex; justify-content: space-around;
      font-size: 12px; color: #888; user-select: none;
    }

    /* Squares */
    .sq {
      width: 64px; height: 64px; border: none; padding: 0;
      cursor: pointer; position: relative;
      display: flex; align-items: center; justify-content: center;
    }
    .sq:focus { outline: none; }
    .light { background: #f0d9b5; }
    .dark  { background: #b58863; }
    .selected.light { background: #f6f669; }
    .selected.dark  { background: #baca2b; }

    /* Pieces */
    .piece-img { width: 100%; height: 100%; pointer-events: none; user-select: none; display: block; }

    /* Legal move indicators */
    .dot-overlay {
      position: absolute; width: 32%; height: 32%;
      border-radius: 50%; background: rgba(0,0,0,0.2);
      pointer-events: none; z-index: 1;
    }
    .ring-overlay {
      position: absolute; inset: 0; border-radius: 50%;
      border: 7px solid rgba(0,0,0,0.2);
      pointer-events: none; z-index: 1; box-sizing: border-box;
    }

    #status { margin: 12px 0; min-height: 24px; font-size: 14px; }
    #controls { margin-top: 10px; }
    .ctrl-btn { padding: 8px 12px; margin-right: 8px; }
    .small { color: #666; font-size: 13px; margin-top: 8px; }

    /* Engine panel */
    #engine-panel { min-width: 210px; }
    #engine-panel h3 { margin: 0 0 10px 0; font-size: 15px; color: #333; border-bottom: 1px solid #ddd; padding-bottom: 6px; }
    .engine-card {
      display: block; width: 100%; text-align: left;
      padding: 8px 12px; margin-bottom: 6px;
      border: 2px solid #ddd; border-radius: 5px;
      background: #fff; cursor: pointer; font-size: 13px;
      transition: border-color 0.12s, background 0.12s;
      box-sizing: border-box;
    }
    .engine-card:hover { border-color: #999; background: #f8f8f8; }
    .engine-card.active { border-color: #4a90d9; background: #eaf3ff; font-weight: bold; color: #1a5fa8; }
    .engine-card .eng-key { display: block; color: #aaa; font-size: 11px; margin-top: 2px; font-weight: normal; }
    .engine-card.active .eng-key { color: #6aaae8; }
    .switch-hint { font-size: 12px; color: #999; margin-top: 8px; }

    /* Side picker */
    #side-picker { display: flex; gap: 10px; margin-bottom: 18px; align-items: center; }
    .side-btn {
      padding: 7px 20px; border: 2px solid #ccc; border-radius: 5px;
      background: #f4f4f4; cursor: pointer; font-size: 14px; font-weight: 600;
      transition: all 0.15s;
    }
    .side-btn:hover { border-color: #888; }
    #playWhiteBtn.chosen { border-color: #555; background: #fff; color: #111; box-shadow: 0 1px 5px rgba(0,0,0,0.15); }
    #playBlackBtn.chosen { border-color: #111; background: #2b2b2b; color: #eee; box-shadow: 0 1px 5px rgba(0,0,0,0.4); }
  </style>
</head>
<body>
  <h2>Antichess &mdash; Good Luck!!</h2>
  <div id="side-picker">
    <span style="font-size:13px;color:#555;font-weight:500;">Play as:</span>
    <button class="side-btn" id="playWhiteBtn">&#9812; White</button>
    <button class="side-btn" id="playBlackBtn">&#9818; Black</button>
  </div>
  <div id="layout">
    <div>
      <div id="status"></div>
      <div id="board-wrap">
        <div id="rank-labels">
          <span>8</span><span>7</span><span>6</span><span>5</span>
          <span>4</span><span>3</span><span>2</span><span>1</span>
        </div>
        <div id="board-col">
          <div id="board"></div>
          <div id="file-labels">
            <span>a</span><span>b</span><span>c</span><span>d</span>
            <span>e</span><span>f</span><span>g</span><span>h</span>
          </div>
        </div>
      </div>
      <div id="controls">
        <button class="ctrl-btn" id="newGameBtn">New Game</button>
      </div>
      <div class="small">Click source square then destination square. Promotions prompt for piece (q/r/b/n/k).</div>
    </div>
    <div id="engine-panel">
      <h3>Choose Engine</h3>
      <div id="engine-list"></div>
      <div class="switch-hint">Switching engine starts a new game.</div>
    </div>
  </div>

  <script>
    const ENGINES = __ENGINES_JSON__;
    let activeEngine = "__ACTIVE_ENGINE__";
    let playingAs = "white";

    const PIECE_BASE = "https://cdn.jsdelivr.net/gh/lichess-org/lila@master/public/piece/maestro/";
    function pieceImgUrl(piece) {
      const c = piece.color === "white" ? "w" : "b";
      return PIECE_BASE + c + piece.symbol.toUpperCase() + ".svg";
    }

    const boardEl = document.getElementById("board");
    const statusEl = document.getElementById("status");
    const newGameBtn = document.getElementById("newGameBtn");

    const engineListEl = document.getElementById("engine-list");
    const playWhiteBtn = document.getElementById("playWhiteBtn");
    const playBlackBtn = document.getElementById("playBlackBtn");

    let current = null;
    let selected = null;

    function updateSideButtons() {
      playWhiteBtn.classList.toggle("chosen", playingAs === "white");
      playBlackBtn.classList.toggle("chosen", playingAs === "black");
    }

    function updateCoordLabels(flipped) {
      const rankEl = document.getElementById("rank-labels");
      const fileEl = document.getElementById("file-labels");
      const ranks = flipped ? ["1","2","3","4","5","6","7","8"] : ["8","7","6","5","4","3","2","1"];
      const files = flipped ? ["h","g","f","e","d","c","b","a"] : ["a","b","c","d","e","f","g","h"];
      rankEl.innerHTML = ranks.map(r => `<span>${r}</span>`).join("");
      fileEl.innerHTML = files.map(f => `<span>${f}</span>`).join("");
    }

    async function setSide(side) {
      if (side === playingAs) return;
      statusEl.textContent = "Starting new game...";
      try {
        const data = await api("/set_side", "POST", { side });
        playingAs = side;
        current = data.state;
        selected = null;
        updateSideButtons();
        updateCoordLabels(playingAs === "black");
        if (current.engine_turn && !current.game_over) {
          statusEl.textContent = "Engine thinking...";
          const moved = await api("/engine_move", "POST", {});
          current = moved.state;
        }
        render();
      } catch (err) {
        statusEl.textContent = "Error: " + err.message;
      }
    }

    playWhiteBtn.onclick = () => setSide("white");
    playBlackBtn.onclick = () => setSide("black");

    function renderEngineList() {
      engineListEl.innerHTML = "";
      for (const eng of ENGINES) {
        const btn = document.createElement("button");
        btn.className = "engine-card" + (eng.name === activeEngine ? " active" : "");
        btn.innerHTML = eng.label + '<span class="eng-key">' + eng.name + "</span>";
        btn.onclick = () => switchEngine(eng.name);
        engineListEl.appendChild(btn);
      }
    }

    async function switchEngine(name) {
      if (name === activeEngine) return;
      statusEl.textContent = "Switching engine...";
      try {
        const data = await api("/switch_engine", "POST", { name });
        activeEngine = name;
        current = data.state;
        selected = null;
        renderEngineList();
        render();
      } catch (err) {
        statusEl.textContent = "Switch failed: " + err.message;
      }
    }

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
      const flipped = (playingAs === "black");

      for (let ri = 0; ri < 8; ri++) {
        const rank = flipped ? ri : 7 - ri;
        for (let fi = 0; fi < 8; fi++) {
          const file = flipped ? 7 - fi : fi;
          const idx = rank * 8 + file;
          const sq = indexToSquare(idx);
          const piece = current.board[idx];
          const isLight = (file + rank) % 2 === 1;
          const isTarget = targets.has(sq);

          const btn = document.createElement("button");
          btn.className = "sq " + (isLight ? "light" : "dark");
          if (selected === sq) btn.classList.add("selected");

          if (piece) {
            const img = document.createElement("img");
            img.src = pieceImgUrl(piece);
            img.className = "piece-img";
            img.draggable = false;
            btn.appendChild(img);
          }

          if (isTarget) {
            const overlay = document.createElement("div");
            overlay.className = piece ? "ring-overlay" : "dot-overlay";
            btn.appendChild(overlay);
          }

          btn.onclick = () => clickSquare(sq);
          boardEl.appendChild(btn);
        }
      }

      statusEl.textContent = current.status;
    }

    async function loadState() {
      const data = await api("/state");
      current = data.state;
      if (current.engine_name && current.engine_name !== activeEngine) {
        activeEngine = current.engine_name;
        renderEngineList();
      }
      playingAs = current.you_are_white ? "white" : "black";
      updateSideButtons();
      updateCoordLabels(playingAs === "black");
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


    renderEngineList();
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

    def switch_engine(self, name: str) -> None:
        self.engine_module = load_engine(name)
        self.engine_name = name
        self.reset()

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
            "engine_name": self.engine_name,
            "engine_label": _engine_label(self.engine_name),
            "you_are_white": self.you_are_white,
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
                body = _build_html(session.engine_name).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if self.path == "/state":
                _json(self, 200, {"ok": True, "state": session.snapshot()})
                return

            if self.path == "/engines":
                engines = [{"name": k, "label": v} for k, v in ENGINE_LABELS.items()]
                _json(self, 200, {"ok": True, "engines": engines})
                return

            _json(self, 404, {"ok": False, "error": "Not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/new_game":
                session.reset()
                _json(self, 200, {"ok": True, "state": session.snapshot()})
                return

            if self.path == "/set_side":
                data = _read_json(self)
                side = str(data.get("side", "")).strip()
                if side not in ("white", "black"):
                    _json(self, 400, {"ok": False, "error": "side must be 'white' or 'black'."})
                    return
                session.you_are_white = (side == "white")
                session.reset()
                _json(self, 200, {"ok": True, "state": session.snapshot()})
                return

            if self.path == "/switch_engine":
                data = _read_json(self)
                name = str(data.get("name", "")).strip()
                if not name:
                    _json(self, 400, {"ok": False, "error": "Missing engine name."})
                    return
                if name not in ENGINE_LABELS:
                    _json(self, 400, {"ok": False, "error": f"Unknown engine: {name}"})
                    return
                try:
                    session.switch_engine(name)
                except EngineContractError as exc:
                    _json(self, 400, {"ok": False, "error": str(exc)})
                    return
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
