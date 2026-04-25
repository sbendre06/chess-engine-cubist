"""Resumable baseline-vs-all tournament runner with incremental saves.

This leaves the frozen `evaluation/` package untouched and instead provides a
wrapper that preserves the same basic matchup/scoring semantics while adding:

- per-game checkpointing to a JSON state file
- a live CSV summary rewritten after each completed game
- resume support for interrupted runs

Examples:
    python tools/resumable_tournament.py --games 20 --depth 3
    python tools/resumable_tournament.py --games 20 --depth 3 --only caveman
    python tools/resumable_tournament.py --resume evaluation/results/tournament-resumable-20260425-120000.state.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import chess
import chess.variant

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.adapter import HarnessAdapter
from evaluation.report import (
    EXPERIMENT_LOG_PATH,
    elo_ci95,
    elo_per_1k_tokens,
    list_engines,
    read_tokens,
    score_to_elo,
    update_experiment_log_winrates,
)


RESULTS_DIR = Path("evaluation/results")
STATE_VERSION = 1
CSV_FIELDS = [
    "engine",
    "prompt_name",
    "components",
    "games",
    "target_games",
    "completed",
    "wins",
    "draws",
    "losses",
    "score",
    "elo_vs_baseline",
    "elo_ci_low",
    "elo_ci_high",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "elapsed_s",
    "elo_per_1k_tokens",
    "avg_plies",
    "avg_game_seconds",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run every engine vs the baseline with per-game checkpoints."
    )
    parser.add_argument("--baseline", default="baseline", help="Baseline engine name.")
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--movetime-ms", type=int, default=None)
    parser.add_argument("--max-plies", type=int, default=600)
    parser.add_argument(
        "--skip",
        action="append",
        default=["_template"],
        help="Engine names to skip. Pass multiple times. Default: _template.",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Restrict to one or more opponent engines. Pass multiple times.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional CSV output path. Defaults to evaluation/results/tournament-resumable-<timestamp>.csv",
    )
    parser.add_argument(
        "--resume",
        type=Path,
        default=None,
        help="Resume from a previous .state.json checkpoint.",
    )
    return parser.parse_args()


def _fmt_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp_path, path)


def _atomic_write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp_path, path)


def _state_match() -> dict[str, Any]:
    return {
        "games_played": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "sum_plies": 0,
        "sum_game_seconds": 0.0,
        "completed": False,
    }


def _initial_state(args: argparse.Namespace) -> dict[str, Any]:
    skip = set(args.skip or []) | {args.baseline}
    opponents = [name for name in list_engines() if name not in skip]
    if args.only:
        wanted = set(args.only)
        opponents = [name for name in opponents if name in wanted]

    if not opponents:
        raise SystemExit(
            f"no opponent engines to run against {args.baseline} (checked: {list_engines()})"
        )

    out_path = args.out
    if out_path is None:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        out_path = RESULTS_DIR / f"tournament-resumable-{timestamp}.csv"
    state_path = out_path.with_suffix(".state.json")

    return {
        "version": STATE_VERSION,
        "created_at_utc": _utc_now(),
        "updated_at_utc": _utc_now(),
        "output_csv": str(out_path),
        "state_path": str(state_path),
        "config": {
            "baseline": args.baseline,
            "games": max(1, args.games),
            "depth": max(1, args.depth),
            "movetime_ms": max(1, args.movetime_ms) if args.movetime_ms is not None else None,
            "max_plies": max(1, args.max_plies),
            "skip": list(args.skip or []),
            "only": list(args.only or []),
        },
        "opponents": opponents,
        "matches": {name: _state_match() for name in opponents},
    }


def _load_state(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        state = json.load(handle)
    if state.get("version") != STATE_VERSION:
        raise SystemExit(
            f"unsupported state version in {path}: {state.get('version')} (expected {STATE_VERSION})"
        )
    return state


def _save_state(state: dict[str, Any]) -> None:
    state["updated_at_utc"] = _utc_now()
    _atomic_write_text(
        Path(state["state_path"]),
        json.dumps(state, indent=2, sort_keys=True) + "\n",
    )


def _score(match: dict[str, Any]) -> float:
    games_played = int(match["games_played"])
    if games_played <= 0:
        return 0.0
    return (float(match["wins"]) + 0.5 * float(match["draws"])) / float(games_played)


def _row_for_opponent(
    opponent: str,
    match: dict[str, Any],
    *,
    target_games: int,
) -> dict[str, Any]:
    games_played = int(match["games_played"])
    score = _score(match)
    elo = score_to_elo(score)
    ci = elo_ci95(score, games_played) if games_played > 0 else None
    tokens = read_tokens(opponent)

    avg_plies = (float(match["sum_plies"]) / games_played) if games_played else 0.0
    avg_game_seconds = (
        float(match["sum_game_seconds"]) / games_played if games_played else 0.0
    )

    return {
        "engine": opponent,
        "prompt_name": tokens.prompt_name,
        "components": tokens.note,
        "games": games_played,
        "target_games": target_games,
        "completed": int(bool(match["completed"])),
        "wins": int(match["wins"]),
        "draws": int(match["draws"]),
        "losses": int(match["losses"]),
        "score": round(score, 3),
        "elo_vs_baseline": round(elo, 1) if elo is not None else None,
        "elo_ci_low": round(ci[0], 1) if ci is not None else None,
        "elo_ci_high": round(ci[1], 1) if ci is not None else None,
        "input_tokens": tokens.input_tokens,
        "output_tokens": tokens.output_tokens,
        "total_tokens": tokens.total_tokens,
        "elapsed_s": tokens.elapsed_s,
        "elo_per_1k_tokens": (
            round(elo_per_1k_tokens(elo, tokens.total_tokens), 2)
            if elo_per_1k_tokens(elo, tokens.total_tokens) is not None
            else None
        ),
        "avg_plies": round(avg_plies, 1),
        "avg_game_seconds": round(avg_game_seconds, 2),
    }


def _write_summary_csv(state: dict[str, Any]) -> None:
    target_games = int(state["config"]["games"])
    rows = [
        _row_for_opponent(opponent, state["matches"][opponent], target_games=target_games)
        for opponent in state["opponents"]
    ]
    _atomic_write_csv(Path(state["output_csv"]), rows)


def _update_experiment_log(state: dict[str, Any]) -> None:
    completed = {
        opponent: _score(state["matches"][opponent])
        for opponent in state["opponents"]
        if state["matches"][opponent]["completed"]
    }
    if completed:
        update_experiment_log_winrates(completed)


def _print_summary(state: dict[str, Any]) -> None:
    rows = []
    target_games = int(state["config"]["games"])
    for opponent in state["opponents"]:
        row = _row_for_opponent(opponent, state["matches"][opponent], target_games=target_games)
        rows.append(row)

    baseline = state["config"]["baseline"]
    print()
    print(f"=== Resumable Results (vs {baseline}) ===")
    header = ("engine", "games", "W-D-L", "done", "Elo", "CI95", "Elo/1kT")
    print("  ".join(f"{h:<14}" for h in header))
    for row in rows:
        wdl = f"{row['wins']}-{row['draws']}-{row['losses']}"
        games = f"{row['games']}/{row['target_games']}"
        cells = (
            row["engine"],
            games,
            wdl,
            row["completed"],
            _fmt_cell(row["elo_vs_baseline"]),
            (
                f"[{row['elo_ci_low']:.1f},{row['elo_ci_high']:.1f}]"
                if row["elo_ci_low"] is not None
                else ""
            ),
            _fmt_cell(row["elo_per_1k_tokens"]),
        )
        print("  ".join(f"{str(c):<14}" for c in cells))


def _play_one_game(
    adapter_a: HarnessAdapter,
    adapter_b: HarnessAdapter,
    *,
    game_index: int,
    max_plies: int,
) -> tuple[str | None, int, float]:
    board = chess.variant.AntichessBoard()
    white = adapter_a if game_index % 2 == 1 else adapter_b
    black = adapter_b if game_index % 2 == 1 else adapter_a

    start = time.perf_counter()
    plies = 0
    while not board.is_game_over(claim_draw=True) and plies < max_plies:
        mover = white if board.turn == chess.WHITE else black
        move = mover.choose_move(board)
        if move not in board.legal_moves:
            raise ValueError(f"Illegal move from {mover.name}: {move.uci()}")
        board.push(move)
        plies += 1

    elapsed = time.perf_counter() - start
    outcome = board.outcome(claim_draw=True)
    winner_name = None
    if outcome is not None and outcome.winner is not None:
        winner_name = white.name if outcome.winner == chess.WHITE else black.name

    return winner_name, plies, elapsed


def _run_opponent(state: dict[str, Any], opponent: str) -> None:
    cfg = state["config"]
    target_games = int(cfg["games"])
    max_plies = int(cfg["max_plies"])
    match = state["matches"][opponent]
    games_played = int(match["games_played"])

    if match["completed"]:
        print(f"--- {opponent} vs {cfg['baseline']} --- already complete ({games_played}/{target_games})")
        return

    print()
    print(
        f"--- {opponent} vs {cfg['baseline']} --- resume at game {games_played + 1}/{target_games}"
    )

    adapter_a = HarnessAdapter(
        opponent,
        depth=int(cfg["depth"]),
        movetime_ms=cfg["movetime_ms"],
    )
    adapter_b = HarnessAdapter(
        cfg["baseline"],
        depth=int(cfg["depth"]),
        movetime_ms=cfg["movetime_ms"],
    )

    try:
        for game_index in range(games_played + 1, target_games + 1):
            winner_name, plies, elapsed = _play_one_game(
                adapter_a,
                adapter_b,
                game_index=game_index,
                max_plies=max_plies,
            )

            match["games_played"] = int(match["games_played"]) + 1
            match["sum_plies"] = int(match["sum_plies"]) + plies
            match["sum_game_seconds"] = float(match["sum_game_seconds"]) + elapsed

            if winner_name is None:
                match["draws"] = int(match["draws"]) + 1
            elif winner_name == adapter_a.name:
                match["wins"] = int(match["wins"]) + 1
            else:
                match["losses"] = int(match["losses"]) + 1

            match["completed"] = int(match["games_played"]) >= target_games
            _save_state(state)
            _write_summary_csv(state)
            _update_experiment_log(state)

            print(
                f"  game {game_index}/{target_games}: "
                f"winner={winner_name or 'draw':<20} plies={plies} time={elapsed:.2f}s "
                f"(saved)"
            )
    finally:
        adapter_a.close()
        adapter_b.close()


def _load_or_init(args: argparse.Namespace) -> dict[str, Any]:
    if args.resume is not None:
        state = _load_state(args.resume)
        print(f"Resuming from {args.resume}")
        return state

    state = _initial_state(args)
    _save_state(state)
    _write_summary_csv(state)
    print(f"Created state file: {state['state_path']}")
    return state


def main() -> None:
    args = _parse_args()
    state = _load_or_init(args)
    cfg = state["config"]

    print(
        "Tournament: "
        f"{cfg['baseline']} vs {state['opponents']}  "
        f"(games={cfg['games']}, depth={cfg['depth']}, movetime_ms={cfg['movetime_ms']})"
    )
    print(f"Live CSV: {state['output_csv']}")
    print(f"Checkpoint: {state['state_path']}")

    try:
        for opponent in state["opponents"]:
            _run_opponent(state, opponent)
    except KeyboardInterrupt:
        print()
        print("Interrupted. Completed games are already saved.")
        print(f"Resume with: python tools/resumable_tournament.py --resume {state['state_path']}")
        return

    _save_state(state)
    _write_summary_csv(state)
    _update_experiment_log(state)
    _print_summary(state)

    print()
    print(f"Wrote {state['output_csv']}")
    print(f"Updated {EXPERIMENT_LOG_PATH} winrates for completed opponents.")


if __name__ == "__main__":
    main()
