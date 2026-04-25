#!/usr/bin/env python3
"""Append a build-session row to experiment_log.csv.

Run this once per Claude Code session, after the session ends. Records the
build-time data (tokens, wall time, interventions). The `engine_winrate`
column is populated automatically by `python -m evaluation.tournament`
after the engine has been played against the baseline.

Token counts: open Claude Code's `/cost` slash command at session end and
copy the input/output token totals.

Usage:
  python log_experiment.py \\
      --name kitchen_sink \\
      --tokens-in 12500 \\
      --tokens-out 3200 \\
      --minutes 45 \\
      --interventions 7
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


LOG_PATH = Path("experiment_log.csv")
FIELDS = [
    "experiment_name",
    "tokens_in",
    "tokens_out",
    "wall_time_minutes",
    "interventions",
    "engine_winrate",
]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Append a build-session row to experiment_log.csv.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--name", required=True, help="Engine / experiment name (matches engines/<name>.py).")
    p.add_argument("--tokens-in", type=int, required=True, help="Input tokens for the session (from /cost).")
    p.add_argument("--tokens-out", type=int, required=True, help="Output tokens for the session (from /cost).")
    p.add_argument("--minutes", type=float, required=True, help="Wall-clock minutes for the session.")
    p.add_argument("--interventions", type=int, required=True, help="How many human messages were sent during the session.")
    return p.parse_args()


def _row_exists(name: str) -> bool:
    if not LOG_PATH.exists():
        return False
    with LOG_PATH.open("r", newline="", encoding="utf-8") as h:
        return any(r["experiment_name"] == name for r in csv.DictReader(h))


def main() -> None:
    args = _parse_args()

    if _row_exists(args.name):
        sys.exit(
            f"a row for experiment_name={args.name} already exists in {LOG_PATH}. "
            "Edit it manually or pick a unique name."
        )

    row = {
        "experiment_name": args.name,
        "tokens_in": args.tokens_in,
        "tokens_out": args.tokens_out,
        "wall_time_minutes": args.minutes,
        "interventions": args.interventions,
        "engine_winrate": "",
    }
    file_exists = LOG_PATH.exists()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=FIELDS)
        if not file_exists:
            w.writeheader()
        w.writerow(row)
    print(f"appended row for {args.name} to {LOG_PATH}")
    print(f"engine_winrate will be filled in next time `python -m evaluation.tournament` runs.")


if __name__ == "__main__":
    main()
