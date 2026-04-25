"""Render the correctness pass/fail matrix as a heatmap PNG.

Reads evaluation/results/correctness/*.json and writes a slide-ready
heatmap to evaluation/results/correctness_matrix.png (or --out path).

Green cells = pass, red cells = fail. Tier 1 and Tier 2 sections are
visually separated by a divider; per-engine T1/T2 totals are annotated
along the bottom.

Usage:
    python -m evaluation.correctness_plot
    python -m evaluation.correctness_plot --out slides/matrix.png
    python -m evaluation.correctness_plot --transpose
    python -m evaluation.correctness_plot --tier 1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

from evaluation.correctness_matrix import RESULTS_DIR, filter_tests, load_all_results


PASS_COLOR = "#2e7d32"   # green
FAIL_COLOR = "#c62828"   # red
DIVIDER_COLOR = "#222222"
TITLE = "Antichess Correctness Suite — per-check pass/fail"


def render_heatmap(
    engines: list[str],
    tests: list[tuple[str, int]],
    matrix: dict[str, dict[str, bool]],
    *,
    transpose: bool,
    show_totals: bool,
    out_path: Path,
    title: str,
    totals_source: list[tuple[str, int]] | None = None,
) -> None:
    """tests are (test_id, tier) tuples in display order.

    totals_source defaults to `tests` -- pass the unfiltered list to make the
    bottom annotation reflect ALL tier scores even when tier 0 rows are hidden.
    """
    if totals_source is None:
        totals_source = tests

    grid = np.array(
        [[1 if matrix[name].get(tid) else 0 for name in engines] for tid, _ in tests],
        dtype=int,
    )
    row_labels = [f"T{tier}  {tid}" for tid, tier in tests]
    col_labels = list(engines)

    if transpose:
        grid = grid.T
        row_labels, col_labels = col_labels, row_labels

    cmap = ListedColormap([FAIL_COLOR, PASS_COLOR])

    n_rows, n_cols = grid.shape
    cell_w = 0.55
    cell_h = 0.42
    fig_w = max(9.0, 5.0 + n_cols * cell_w)
    fig_h = max(5.5, 3.0 + n_rows * cell_h)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.imshow(grid, cmap=cmap, aspect="auto", vmin=0, vmax=1)

    # Move x-axis labels to the TOP so they don't collide with totals
    ax.set_xticks(np.arange(n_cols))
    ax.set_yticks(np.arange(n_rows))
    ax.set_xticklabels(col_labels, rotation=35, ha="left", fontsize=9)
    ax.set_yticklabels(row_labels, fontsize=9, family="monospace")
    ax.xaxis.set_ticks_position("top")
    ax.xaxis.set_label_position("top")
    ax.tick_params(axis="x", which="major", pad=4)
    ax.tick_params(axis="y", which="major", pad=2)

    # Cell text glyphs
    for i in range(n_rows):
        for j in range(n_cols):
            ch = "✓" if grid[i, j] == 1 else "✗"
            ax.text(j, i, ch, ha="center", va="center",
                    color="white", fontsize=11, fontweight="bold")

    # White gridlines between cells
    ax.set_xticks(np.arange(-0.5, n_cols, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.0)
    ax.tick_params(which="minor", bottom=False, left=False, top=False, right=False)

    # Tier divider lines
    if not transpose:
        for i, (_, tier) in enumerate(tests[:-1]):
            if tier != tests[i + 1][1]:
                ax.axhline(i + 0.5, color=DIVIDER_COLOR, linewidth=2.0)
    else:
        for j, (_, tier) in enumerate(tests[:-1]):
            if tier != tests[j + 1][1]:
                ax.axvline(j + 0.5, color=DIVIDER_COLOR, linewidth=2.0)

    # Per-engine totals -- placed below the matrix in their own annotated row.
    # Use totals_source (unfiltered) so T0 score still shows when T0 rows are hidden.
    def _tier_label(name: str) -> list[str]:
        out = []
        for tier_n, tag in ((0, "T0"), (1, "T1"), (2, "T2")):
            n = sum(1 for tid, t in totals_source if t == tier_n)
            if not n:
                continue
            p = sum(1 for tid, t in totals_source if t == tier_n and matrix[name].get(tid))
            out.append(f"{tag} {p}/{n}")
        return out

    if show_totals and not transpose:
        for j, name in enumerate(engines):
            ax.text(j, n_rows + 0.05, "\n".join(_tier_label(name)),
                    ha="center", va="top", fontsize=8.5, family="monospace",
                    color="#222222",
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="#f3f3f3",
                              edgecolor="#cccccc", linewidth=0.6))
        # Pad the bottom so the annotation has room (3 tiers needs more)
        ax.set_ylim(n_rows + 2.0, -0.5)

    if show_totals and transpose:
        for i, name in enumerate(engines):
            ax.text(n_cols + 0.05, i, "  ".join(_tier_label(name)),
                    ha="left", va="center", fontsize=8.5, family="monospace",
                    color="#222222",
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="#f3f3f3",
                              edgecolor="#cccccc", linewidth=0.6))
        ax.set_xlim(-0.5, n_cols + 3.5)

    ax.set_title(title, fontsize=13, pad=18, loc="left", fontweight="bold")
    plt.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Plot the correctness matrix as a heatmap PNG")
    p.add_argument("--out", type=Path,
                   default=Path("evaluation/results/correctness_matrix.png"),
                   help="output PNG path (default: evaluation/results/correctness_matrix.png)")
    p.add_argument("--transpose", action="store_true",
                   help="rows = engines, cols = tests (default: rows = tests)")
    p.add_argument("--tier", type=int, choices=(0, 1, 2),
                   help="filter to one tier only")
    p.add_argument("--include-tier0", action="store_true",
                   help="include Tier 0 (50 broad coverage tests). Default: omit, "
                        "since they're typically all-pass and add visual noise. "
                        "Tier 0 totals still appear in the bottom annotation.")
    p.add_argument("--no-totals", action="store_true",
                   help="omit per-engine T0/T1/T2 score annotations")
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR,
                   help="override results directory")
    p.add_argument("--title", type=str, default=TITLE)
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    engines, test_order, matrix = load_all_results(args.results_dir)
    if args.tier is not None:
        tests = filter_tests(test_order, args.tier)
    else:
        tests = test_order if args.include_tier0 else [t for t in test_order if t[1] != 0]

    render_heatmap(
        engines, tests, matrix,
        transpose=args.transpose,
        show_totals=not args.no_totals,
        out_path=args.out,
        title=args.title,
        # Pass full test_order so totals annotation can include T0 even when rows are filtered
        totals_source=test_order,
    )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
