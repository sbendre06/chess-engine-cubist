"""Every engine vs the baseline; produces the ablation results table.

Usage:
    python -m evaluation.tournament --baseline baseline --games 20 --depth 3
"""

from __future__ import annotations

import argparse
import csv
import random
import time
from pathlib import Path

from evaluation.adapter import HarnessAdapter
from evaluation.match_loop import MatchConfig, run_match
from evaluation.openings import generate_balanced_openings
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
CSV_FIELDS = [
    "engine",
    "prompt_name",
    "components",
    "games",
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
    parser = argparse.ArgumentParser(description="Run every engine vs the baseline.")
    parser.add_argument("--baseline", default="baseline", help="Baseline engine name.")
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--movetime-ms", type=int, default=None)
    parser.add_argument(
        "--skip",
        action="append",
        default=["_template"],
        help="Engine names to skip. Pass multiple times. Default: _template.",
    )
    parser.add_argument("--seed", type=int, default=None,
                        help="Seed for opening generation + eval noise (default: random).")
    parser.add_argument("--noise-cp", type=int, default=3,
                        help="±cp uniform jitter on evaluate_board (0 disables).")
    parser.add_argument("--opening-plies", type=int, default=4,
                        help="Random plies from start to build each opening (0 disables openings).")
    parser.add_argument("--balance-threshold", type=int, default=200,
                        help="Reject opening if |baseline_eval_cp| exceeds this.")
    parser.add_argument("--opening-eval-depth", type=int, default=2,
                        help="Search depth for the balance-check evaluation.")
    return parser.parse_args()


def _fmt_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def main() -> None:
    args = _parse_args()
    all_engines = list_engines()
    skip = set(args.skip or []) | {args.baseline}
    opponents = [name for name in all_engines if name not in skip]

    if not opponents:
        print(f"no opponent engines to run against {args.baseline} (checked: {all_engines})")
        return

    seed = args.seed if args.seed is not None else random.randrange(2**31)
    master_rng = random.Random(seed)
    print(
        f"Tournament: {args.baseline} vs {opponents}  "
        f"(games={args.games}, depth={args.depth}, seed={seed}, "
        f"noise_cp={args.noise_cp}, opening_plies={args.opening_plies})"
    )

    openings: list[str] = []
    if args.opening_plies > 0:
        opening_count = max(1, args.games // 2)
        openings = generate_balanced_openings(
            opening_count,
            plies=args.opening_plies,
            balance_threshold_cp=args.balance_threshold,
            reference_engine=args.baseline,
            eval_depth=args.opening_eval_depth,
            rng=random.Random(master_rng.randrange(2**31)),
        )
        print(f"Generated {len(openings)} balanced opening(s).")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    out_path = RESULTS_DIR / f"tournament-{timestamp}.csv"

    rows: list[dict] = []
    name_to_winrate: dict[str, float] = {}
    for opponent in opponents:
        print()
        print(f"--- {opponent} vs {args.baseline} ---")
        # Engine A = the opponent (so Elo(A-B) reads as "opponent vs baseline").
        adapter_a = HarnessAdapter(
            opponent, depth=args.depth, movetime_ms=args.movetime_ms,
            noise_cp=args.noise_cp,
            rng=random.Random(master_rng.randrange(2**31)),
        )
        adapter_b = HarnessAdapter(
            args.baseline, depth=args.depth, movetime_ms=args.movetime_ms,
            noise_cp=args.noise_cp,
            rng=random.Random(master_rng.randrange(2**31)),
        )
        config = MatchConfig(
            games=max(1, args.games),
            depth=args.depth,
            movetime_ms=args.movetime_ms,
            openings=openings or None,
        )
        report = run_match(adapter_a, adapter_b, config)

        tokens = read_tokens(opponent)
        score = report.score_a
        elo = score_to_elo(score)
        ci = elo_ci95(score, report.games)
        row = {
            "engine": opponent,
            "prompt_name": tokens.prompt_name,
            "components": tokens.note,
            "games": report.games,
            "wins": report.engine_a_wins,
            "draws": report.draws,
            "losses": report.engine_b_wins,
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
            "avg_plies": round(report.avg_plies, 1),
            "avg_game_seconds": round(report.avg_game_seconds, 2),
        }
        rows.append(row)
        name_to_winrate[opponent] = score

    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print()
    print("=== Ablation Results (vs " + args.baseline + ") ===")
    header = ("engine", "components", "W-D-L", "Elo", "CI95", "in_tok", "out_tok", "Elo/1kT")
    print("  ".join(f"{h:<14}" for h in header))
    for row in rows:
        wdl = f"{row['wins']}-{row['draws']}-{row['losses']}"
        elo = _fmt_cell(row["elo_vs_baseline"])
        ci = (
            f"[{row['elo_ci_low']:.1f},{row['elo_ci_high']:.1f}]"
            if row["elo_ci_low"] is not None
            else ""
        )
        cells = (
            row["engine"],
            row["components"] or "-",
            wdl,
            elo,
            ci,
            row["input_tokens"],
            row["output_tokens"],
            _fmt_cell(row["elo_per_1k_tokens"]),
        )
        print("  ".join(f"{str(c):<14}" for c in cells))
    update_experiment_log_winrates(name_to_winrate)

    print()
    print(f"Wrote {out_path}")
    print(f"Updated {EXPERIMENT_LOG_PATH} winrates for: {', '.join(sorted(name_to_winrate))}")


if __name__ == "__main__":
    main()
