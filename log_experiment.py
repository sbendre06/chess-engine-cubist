#!/usr/bin/env python3
"""Append a session row to experiment_log.csv.

Run this once per Claude Code session, after the session ends.

Required fields come from the session itself; engine_winrate can be filled
later (after running a tournament) by passing --winrate, or omitted now and
back-filled by hand.

Token counts: open Claude Code's `/cost` slash command at session end and
copy the input/output token totals.

Usage:
  python log_experiment.py \\
      --name kitchen_sink \\
      --tokens-in 12500 \\
      --tokens-out 3200 \\
      --minutes 45 \\
      --interventions 7 \\
      --winrate 0.65

  # winrate not yet known? omit it:
  python log_experiment.py --name kitchen_sink \\
      --tokens-in 12500 --tokens-out 3200 --minutes 45 --interventions 7

  # already-logged engine, fill in the winrate column:
  python log_experiment.py --name kitchen_sink --winrate 0.65 --update-winrate
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
        description="Append (or update) a session row in experiment_log.csv.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--name", required=True, help="Engine / experiment name (matches engines/<name>.py).")
    p.add_argument("--tokens-in", type=int, help="Input tokens for the session (from /cost).")
    p.add_argument("--tokens-out", type=int, help="Output tokens for the session (from /cost).")
    p.add_argument("--minutes", type=float, help="Wall-clock minutes for the session.")
    p.add_argument("--interventions", type=int, help="How many human messages were sent during the session.")
    p.add_argument("--winrate", type=float, default=None, help="Win rate vs baseline, 0.0-1.0. Optional now.")
    p.add_argument(
        "--update-winrate",
        action="store_true",
        help="Update an existing row's engine_winrate column instead of appending a new row. "
             "Requires --name and --winrate; other fields ignored.",
    )
    return p.parse_args()


def _read_rows() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    with LOG_PATH.open("r", newline="", encoding="utf-8") as h:
        return list(csv.DictReader(h))


def _write_rows(rows: list[dict]) -> None:
    with LOG_PATH.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def _append_row(row: dict) -> None:
    file_exists = LOG_PATH.exists()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=FIELDS)
        if not file_exists:
            w.writeheader()
        w.writerow(row)


def main() -> None:
    args = _parse_args()

    if args.update_winrate:
        if args.winrate is None:
            sys.exit("--update-winrate requires --winrate")
        rows = _read_rows()
        if not rows:
            sys.exit(f"{LOG_PATH} is empty or missing; nothing to update")
        target = next((r for r in rows if r["experiment_name"] == args.name), None)
        if target is None:
            sys.exit(f"no row in {LOG_PATH} with experiment_name={args.name}")
        target["engine_winrate"] = f"{args.winrate}"
        _write_rows(rows)
        print(f"updated engine_winrate={args.winrate} for {args.name} in {LOG_PATH}")
        return

    required = ("tokens_in", "tokens_out", "minutes", "interventions")
    missing = [f for f in required if getattr(args, f.replace("-", "_")) is None]
    if missing:
        sys.exit(
            "missing required arguments: " + ", ".join(f"--{m.replace('_', '-')}" for m in missing)
        )

    row = {
        "experiment_name": args.name,
        "tokens_in": args.tokens_in,
        "tokens_out": args.tokens_out,
        "wall_time_minutes": args.minutes,
        "interventions": args.interventions,
        "engine_winrate": f"{args.winrate}" if args.winrate is not None else "",
    }
    _append_row(row)
    print(f"appended row for {args.name} to {LOG_PATH}")


if __name__ == "__main__":
    main()
