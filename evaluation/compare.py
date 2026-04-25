"""Head-to-head comparison of two engines.

Usage:
    python -m evaluation.compare --a baseline --b _template --games 20 --depth 3
"""

from __future__ import annotations

import argparse

from evaluation.adapter import HarnessAdapter
from evaluation.match_loop import MatchConfig, run_match
from evaluation.report import elo_ci95, elo_per_1k_tokens, read_tokens, score_to_elo


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Head-to-head two-engine match.")
    parser.add_argument("--a", required=True, help="Engine A name (under engines/).")
    parser.add_argument("--b", required=True, help="Engine B name (under engines/).")
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--movetime-ms", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    adapter_a = HarnessAdapter(args.a, depth=args.depth, movetime_ms=args.movetime_ms)
    adapter_b = HarnessAdapter(args.b, depth=args.depth, movetime_ms=args.movetime_ms)
    config = MatchConfig(games=max(1, args.games), depth=args.depth, movetime_ms=args.movetime_ms)

    print(f"Match: {args.a} vs {args.b}  (games={args.games}, depth={args.depth})")
    report = run_match(adapter_a, adapter_b, config)

    score_a = report.score_a
    elo_ab = score_to_elo(score_a)
    ci = elo_ci95(score_a, report.games)
    tokens_a = read_tokens(args.a)
    tokens_b = read_tokens(args.b)

    print()
    print("=== Match Summary ===")
    print(f"{'':24}{'A=' + args.a:<24}{'B=' + args.b:<24}")
    print(f"{'Wins':24}{report.engine_a_wins:<24}{report.engine_b_wins:<24}")
    print(f"{'Draws':24}{report.draws}")
    print(f"{'Score A':24}{score_a:.3f}")
    if elo_ab is None:
        print(f"{'Elo(A-B)':24}undefined (0% or 100%)")
    else:
        print(f"{'Elo(A-B)':24}{elo_ab:+.1f}")
    if ci is not None:
        print(f"{'95% CI':24}[{ci[0]:+.1f}, {ci[1]:+.1f}]")
    print(f"{'Avg plies/game':24}{report.avg_plies:.1f}")
    print(f"{'Avg seconds/game':24}{report.avg_game_seconds:.2f}")

    print()
    print("=== Token Cost ===")
    print(f"{'':24}{'A=' + args.a:<24}{'B=' + args.b:<24}")
    print(f"{'prompt_name':24}{tokens_a.prompt_name:<24}{tokens_b.prompt_name:<24}")
    print(f"{'input_tokens':24}{tokens_a.input_tokens:<24}{tokens_b.input_tokens:<24}")
    print(f"{'output_tokens':24}{tokens_a.output_tokens:<24}{tokens_b.output_tokens:<24}")
    print(f"{'elapsed_s':24}{tokens_a.elapsed_s:<24}{tokens_b.elapsed_s:<24}")

    elo_per_kt = elo_per_1k_tokens(elo_ab, tokens_a.total_tokens)
    if elo_per_kt is not None:
        print(f"{'Elo/1k_tok (A over B)':24}{elo_per_kt:+.2f}")


if __name__ == "__main__":
    main()
