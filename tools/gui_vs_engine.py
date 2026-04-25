#!/usr/bin/env python3
"""
Play antichess vs any engines/<name>.py in a simple Tkinter GUI.

Examples:
  .venv/bin/python tools/gui_vs_engine.py --engine baseline
  .venv/bin/python tools/gui_vs_engine.py --engine yesarch_yessttrat_noplan --you black --depth 4
  .venv/bin/python tools/gui_vs_engine.py --engine baseline --movetime 500
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import threading
import tkinter as tk
from tkinter import simpledialog

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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GUI antichess vs any engines/<name>.py.")
    parser.add_argument("--engine", default="baseline",
                        help="Engine module name under engines/ (e.g. baseline, yesarch_yessttrat_noplan).")
    parser.add_argument("--you", choices=["white", "black"], default="white", help="Choose your side.")
    parser.add_argument("--depth", type=int, default=3, help="Fixed search depth.")
    parser.add_argument("--movetime", type=int, default=None, help="Engine time per move in ms.")
    return parser.parse_args()


class AntichessApp:
    def __init__(self, args: argparse.Namespace) -> None:
        try:
            self.engine_module = load_engine(args.engine)
        except EngineContractError as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(2)

        self.engine_name = args.engine
        self.root = tk.Tk()
        self.root.title(f"Cubist AntiChess — {args.engine}")

        self.human_is_white = args.you == "white"
        self.board = chess.variant.AntichessBoard()

        self.config = SearchConfig(max_depth=max(1, args.depth))
        if args.movetime is not None and args.movetime > 0:
            self.config.movetime_ms = args.movetime

        self.selected_square: int | None = None
        self.is_engine_thinking = False
        self.square_buttons: dict[int, tk.Button] = {}

        container = tk.Frame(self.root, padx=8, pady=8)
        container.pack()

        self.status_var = tk.StringVar()
        self.status = tk.Label(container, textvariable=self.status_var, anchor="w", justify="left")
        self.status.grid(row=0, column=0, columnspan=8, sticky="we", pady=(0, 8))

        board_frame = tk.Frame(container, bd=1, relief=tk.SOLID)
        board_frame.grid(row=1, column=0, columnspan=8)
        for rank in range(8):
            for file_ in range(8):
                square = chess.square(file_, 7 - rank)
                btn = tk.Button(
                    board_frame,
                    width=4,
                    height=2,
                    font=("Arial", 22),
                    command=lambda sq=square: self.on_square_click(sq),
                )
                btn.grid(row=rank, column=file_)
                self.square_buttons[square] = btn

        control_frame = tk.Frame(container)
        control_frame.grid(row=2, column=0, columnspan=8, sticky="we", pady=(8, 0))
        tk.Button(control_frame, text="New Game", command=self.new_game).pack(side=tk.LEFT)
        tk.Button(control_frame, text="Quit", command=self.root.destroy).pack(side=tk.LEFT, padx=8)

        self.render()
        self.maybe_start_engine_turn()

    def run(self) -> None:
        self.root.mainloop()

    def new_game(self) -> None:
        if self.is_engine_thinking:
            return
        self.board.reset()
        self.selected_square = None
        self.render()
        self.maybe_start_engine_turn()

    def on_square_click(self, square: int) -> None:
        if self.is_engine_thinking or self.board.is_game_over(claim_draw=True):
            return
        if not self._is_human_turn():
            return

        board = self.board
        piece = board.piece_at(square)
        legal_moves = list(board.legal_moves)

        if self.selected_square is None:
            if piece is not None and piece.color == board.turn:
                self.selected_square = square
                self.render()
            return

        if square == self.selected_square:
            self.selected_square = None
            self.render()
            return

        chosen = self._resolve_move(self.selected_square, square, legal_moves)
        if chosen is None:
            if piece is not None and piece.color == board.turn:
                self.selected_square = square
            else:
                self.selected_square = None
            self.render()
            return

        self.board.push(chosen)
        self.selected_square = None
        self.render()
        self.maybe_start_engine_turn()

    def _resolve_move(self, from_sq: int, to_sq: int, legal_moves: list[chess.Move]) -> chess.Move | None:
        candidates = [m for m in legal_moves if m.from_square == from_sq and m.to_square == to_sq]
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        promote_choice = simpledialog.askstring(
            "Promotion",
            "Promote to one of: q, r, b, n, k",
            parent=self.root,
        )
        if not promote_choice:
            return None
        symbol = promote_choice.strip().lower()
        promo_map = {
            "q": chess.QUEEN,
            "r": chess.ROOK,
            "b": chess.BISHOP,
            "n": chess.KNIGHT,
            "k": chess.KING,
        }
        piece_type = promo_map.get(symbol)
        if piece_type is None:
            return None
        for move in candidates:
            if move.promotion == piece_type:
                return move
        return None

    def _is_human_turn(self) -> bool:
        turn = self.board.turn
        return (turn == chess.WHITE and self.human_is_white) or (turn == chess.BLACK and not self.human_is_white)

    def maybe_start_engine_turn(self) -> None:
        if self.board.is_game_over(claim_draw=True):
            self.render()
            return
        if self._is_human_turn():
            return

        self.is_engine_thinking = True
        self.status_var.set("Engine thinking...")
        self._set_board_enabled(False)

        def worker() -> None:
            board_copy = self.board.copy(stack=True)
            result = iterative_deepening(board_copy, self.engine_module, self.config)
            move_uci = result.best_move_uci
            self.root.after(0, lambda: self._apply_engine_result(move_uci, result))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_engine_result(self, move_uci: str | None, result) -> None:
        legal = list(self.board.legal_moves)
        if legal:
            if move_uci is not None:
                move = chess.Move.from_uci(move_uci)
                chosen = move if move in self.board.legal_moves else legal[0]
            else:
                chosen = legal[0]
            self.board.push(chosen)

        self.is_engine_thinking = False
        self._set_board_enabled(True)
        self.status_var.set(
            f"Engine: depth={result.depth_completed}, score={result.score_cp}, "
            f"nodes={result.nodes}, time={int(result.elapsed_ms)}ms"
        )
        self.render()

    def _set_board_enabled(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for btn in self.square_buttons.values():
            btn.configure(state=state)

    def render(self) -> None:
        board = self.board

        for square, btn in self.square_buttons.items():
            piece = board.piece_at(square)
            text = UNICODE_PIECE.get(piece.symbol(), "") if piece else ""

            file_ = chess.square_file(square)
            rank = chess.square_rank(square)
            is_light = (file_ + rank) % 2 == 1
            base = "#f0d9b5" if is_light else "#b58863"

            bg = base
            if self.selected_square == square:
                bg = "#ffd966"
            elif self.selected_square is not None:
                legal_targets = {
                    m.to_square
                    for m in board.legal_moves
                    if m.from_square == self.selected_square
                }
                if square in legal_targets:
                    bg = "#93c47d"

            btn.configure(text=text, bg=bg, activebackground=bg)

        if self.board.is_game_over(claim_draw=True):
            outcome = self.board.outcome(claim_draw=True)
            if outcome is None or outcome.winner is None:
                self.status_var.set("Game over: draw")
            else:
                winner = "White" if outcome.winner == chess.WHITE else "Black"
                self.status_var.set(f"Game over: {winner} wins (antichess rules)")
        elif not self.is_engine_thinking:
            turn = "White" if board.turn == chess.WHITE else "Black"
            side = "You" if self._is_human_turn() else "Engine"
            self.status_var.set(f"{turn} to move ({side})")


def main() -> None:
    args = _parse_args()
    app = AntichessApp(args)
    app.run()


if __name__ == "__main__":
    main()
