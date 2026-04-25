"""Render the per-engine x per-check pass/fail matrix from correctness JSON.

Reads evaluation/results/correctness/*.json (written by `evaluation.correctness`)
and prints a table to stdout in markdown (default), csv, or plain text.

Usage:
    python -m evaluation.correctness_matrix
    python -m evaluation.correctness_matrix --format csv > matrix.csv
    python -m evaluation.correctness_matrix --format plain
    python -m evaluation.correctness_matrix --transpose      # tests as columns
    python -m evaluation.correctness_matrix --tier 1         # T1 only
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


RESULTS_DIR = Path("evaluation/results/correctness")
PASS_GLYPH = "PASS"
FAIL_GLYPH = "FAIL"
PASS_MD = "✅"
FAIL_MD = "❌"


def load_all_results(results_dir: Path) -> tuple[list[str], list[tuple[str, int]], dict[str, dict[str, bool]]]:
    """Returns (engine_names, [(test_id, tier), ...], {engine: {test_id: passed}})."""
    engine_paths = sorted(results_dir.glob("*.json"))
    if not engine_paths:
        raise SystemExit(f"no result JSONs found in {results_dir}; "
                         f"run `python -m evaluation.correctness --all` first")

    engines: list[str] = []
    test_order: list[tuple[str, int]] = []
    matrix: dict[str, dict[str, bool]] = {}

    for path in engine_paths:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        name = payload["engine_name"]
        engines.append(name)
        per_test: dict[str, bool] = {}
        for r in payload["results"]:
            per_test[r["test_id"]] = bool(r["passed"])
            if not test_order or all(t[0] != r["test_id"] for t in test_order):
                test_order.append((r["test_id"], int(r["tier"])))
        matrix[name] = per_test

    return engines, test_order, matrix


def filter_tests(test_order: list[tuple[str, int]], tier: int | None) -> list[tuple[str, int]]:
    if tier is None:
        return test_order
    return [t for t in test_order if t[1] == tier]


def render_markdown(engines, tests, matrix, transpose, totals) -> str:
    pass_g, fail_g = PASS_MD, FAIL_MD
    lines: list[str] = []
    if transpose:
        # rows = engines, cols = tests
        header = ["engine"] + [f"T{tier} {tid}" for tid, tier in tests]
        if totals:
            header += ["T1", "T2"]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "---|" * len(header))
        for name in engines:
            cells = [pass_g if matrix[name].get(tid) else fail_g for tid, _ in tests]
            row = [name] + cells
            if totals:
                t1p = sum(1 for tid, t in tests if t == 1 and matrix[name].get(tid))
                t1n = sum(1 for tid, t in tests if t == 1)
                t2p = sum(1 for tid, t in tests if t == 2 and matrix[name].get(tid))
                t2n = sum(1 for tid, t in tests if t == 2)
                row += [f"{t1p}/{t1n}", f"{t2p}/{t2n}"]
            lines.append("| " + " | ".join(row) + " |")
    else:
        # rows = tests, cols = engines (default)
        header = ["Test (tier)"] + engines
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "---|" * len(header))
        for tid, tier in tests:
            cells = [pass_g if matrix[name].get(tid) else fail_g for name in engines]
            lines.append(f"| T{tier} `{tid}` | " + " | ".join(cells) + " |")
        if totals:
            t1_row = ["**Tier 1 total**"]
            t2_row = ["**Tier 2 total**"]
            for name in engines:
                t1p = sum(1 for tid, t in tests if t == 1 and matrix[name].get(tid))
                t1n = sum(1 for tid, t in tests if t == 1)
                t2p = sum(1 for tid, t in tests if t == 2 and matrix[name].get(tid))
                t2n = sum(1 for tid, t in tests if t == 2)
                t1_row.append(f"{t1p}/{t1n}")
                t2_row.append(f"{t2p}/{t2n}")
            lines.append("| " + " | ".join(t1_row) + " |")
            lines.append("| " + " | ".join(t2_row) + " |")
    return "\n".join(lines) + "\n"


def render_csv(engines, tests, matrix, transpose, totals) -> str:
    buf = []
    writer = csv.writer(_LineWriter(buf))
    if transpose:
        header = ["engine"] + [f"T{tier}_{tid}" for tid, tier in tests]
        if totals:
            header += ["T1_score", "T2_score"]
        writer.writerow(header)
        for name in engines:
            row = [name] + ["pass" if matrix[name].get(tid) else "fail" for tid, _ in tests]
            if totals:
                t1p = sum(1 for tid, t in tests if t == 1 and matrix[name].get(tid))
                t1n = sum(1 for tid, t in tests if t == 1)
                t2p = sum(1 for tid, t in tests if t == 2 and matrix[name].get(tid))
                t2n = sum(1 for tid, t in tests if t == 2)
                row += [f"{t1p}/{t1n}", f"{t2p}/{t2n}"]
            writer.writerow(row)
    else:
        writer.writerow(["test_id", "tier"] + engines)
        for tid, tier in tests:
            writer.writerow([tid, tier] + ["pass" if matrix[name].get(tid) else "fail" for name in engines])
        if totals:
            for tier_n, label in ((1, "TIER1_TOTAL"), (2, "TIER2_TOTAL")):
                row = [label, tier_n]
                for name in engines:
                    p = sum(1 for tid, t in tests if t == tier_n and matrix[name].get(tid))
                    n = sum(1 for tid, t in tests if t == tier_n)
                    row.append(f"{p}/{n}")
                writer.writerow(row)
    return "".join(buf)


def render_plain(engines, tests, matrix, transpose, totals) -> str:
    pass_g, fail_g = PASS_GLYPH, FAIL_GLYPH
    if transpose:
        col_w = max(len(n) for n in engines) + 2
        test_labels = [f"T{t} {tid}" for tid, t in tests]
        for label in test_labels:
            col_w = max(col_w, len(label) + 2)
        header = "engine".ljust(col_w) + "".join(label.ljust(col_w) for label in test_labels)
        if totals:
            header += "T1".ljust(8) + "T2".ljust(8)
        lines = [header, "-" * len(header)]
        for name in engines:
            cells = [(pass_g if matrix[name].get(tid) else fail_g).ljust(col_w) for tid, _ in tests]
            line = name.ljust(col_w) + "".join(cells)
            if totals:
                t1p = sum(1 for tid, t in tests if t == 1 and matrix[name].get(tid))
                t1n = sum(1 for tid, t in tests if t == 1)
                t2p = sum(1 for tid, t in tests if t == 2 and matrix[name].get(tid))
                t2n = sum(1 for tid, t in tests if t == 2)
                line += f"{t1p}/{t1n}".ljust(8) + f"{t2p}/{t2n}".ljust(8)
            lines.append(line)
        return "\n".join(lines) + "\n"
    else:
        test_col = max(len(f"T{t} {tid}") for tid, t in tests) + 2
        eng_col = max(max(len(n) for n in engines), 6) + 2
        header = "test".ljust(test_col) + "".join(n.ljust(eng_col) for n in engines)
        lines = [header, "-" * len(header)]
        for tid, tier in tests:
            cells = [(pass_g if matrix[name].get(tid) else fail_g).ljust(eng_col) for name in engines]
            lines.append(f"T{tier} {tid}".ljust(test_col) + "".join(cells))
        if totals:
            for tier_n, label in ((1, "Tier 1 total"), (2, "Tier 2 total")):
                cells = []
                for name in engines:
                    p = sum(1 for tid, t in tests if t == tier_n and matrix[name].get(tid))
                    n = sum(1 for tid, t in tests if t == tier_n)
                    cells.append(f"{p}/{n}".ljust(eng_col))
                lines.append(label.ljust(test_col) + "".join(cells))
        return "\n".join(lines) + "\n"


class _LineWriter:
    """csv.writer wants a file-like; this just appends to a list."""
    def __init__(self, sink: list[str]) -> None:
        self.sink = sink
    def write(self, s: str) -> int:
        self.sink.append(s)
        return len(s)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Render the correctness pass/fail matrix")
    p.add_argument("--format", choices=("markdown", "csv", "plain"), default="markdown")
    p.add_argument("--transpose", action="store_true",
                   help="rows = engines, cols = tests (default: rows = tests, cols = engines)")
    p.add_argument("--tier", type=int, choices=(1, 2),
                   help="filter to one tier only")
    p.add_argument("--no-totals", action="store_true",
                   help="omit per-engine T1/T2 score rows/columns")
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR,
                   help="override results directory")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    engines, test_order, matrix = load_all_results(args.results_dir)
    tests = filter_tests(test_order, args.tier)
    totals = not args.no_totals and args.tier is None

    if args.format == "markdown":
        out = render_markdown(engines, tests, matrix, args.transpose, totals)
    elif args.format == "csv":
        out = render_csv(engines, tests, matrix, args.transpose, totals)
    else:
        out = render_plain(engines, tests, matrix, args.transpose, totals)

    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
