"""Hidden antichess correctness suite.

Two-tier evaluation per engine:
  Tier 1 -- rule compliance, calling Core 3 primitives directly on curated FENs.
  Tier 2 -- strategic decision quality, driving the harness's iterative search
            at fixed depth and inspecting the chosen root move.

CLI:
    python -m evaluation.correctness --engine baseline
    python -m evaluation.correctness --all [--depth 4] [--json]

Per-engine results are written as JSON to evaluation/results/correctness/<name>.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import ModuleType

import chess
import chess.variant

from evaluation.correctness_fixtures import (
    TIER0_FIXTURES,
    TIER1_FIXTURES,
    TIER2_FIXTURES,
    Tier1Fixture,
    Tier2Fixture,
)
from harness.engine import SearchConfig, iterative_deepening
from harness.loader import load_engine
from evaluation.report import list_engines


RESULTS_DIR = Path("evaluation/results/correctness")


@dataclass
class TestResult:
    test_id: str
    tier: int
    passed: bool
    detail: str
    elapsed_s: float


@dataclass
class EngineCorrectnessReport:
    engine_name: str
    tier0_passed: int
    tier0_total: int
    tier1_passed: int
    tier1_total: int
    tier2_passed: int
    tier2_total: int
    results: list[TestResult] = field(default_factory=list)

    @property
    def tier0_pass_rate(self) -> float:
        return self.tier0_passed / self.tier0_total if self.tier0_total else 0.0

    @property
    def tier1_pass_rate(self) -> float:
        return self.tier1_passed / self.tier1_total if self.tier1_total else 0.0

    @property
    def tier2_pass_rate(self) -> float:
        return self.tier2_passed / self.tier2_total if self.tier2_total else 0.0


def _filter_legal(board: chess.variant.AntichessBoard, candidates) -> set[str]:
    legal = set(board.legal_moves)
    return {m.uci() for m in candidates if m in legal}


def _run_tier1_fixture(engine: ModuleType, fx: Tier1Fixture, tier: int = 1) -> TestResult:
    start = time.perf_counter()
    board = chess.variant.AntichessBoard(fx.fen)
    legal_uci = {m.uci() for m in board.legal_moves}

    try:
        if fx.rule == "move_gen_superset":
            candidates = engine.get_pseudo_legal_moves(board)
            engine_filtered = _filter_legal(board, candidates)
            missing = legal_uci - engine_filtered
            passed = not missing
            detail = "ok" if passed else f"engine dropped legal moves: {sorted(missing)}"

        elif fx.rule == "legal_moves_exact":
            candidates = engine.get_pseudo_legal_moves(board)
            engine_filtered = _filter_legal(board, candidates)
            expected_set = set(fx.expected["legal_uci"])
            missing = expected_set - engine_filtered
            extra = engine_filtered - expected_set
            passed = not missing and not extra
            if passed:
                detail = "ok"
            else:
                parts = []
                if missing:
                    parts.append(f"missing={sorted(missing)}")
                if extra:
                    parts.append(f"unexpected={sorted(extra)}")
                detail = "; ".join(parts)

        elif fx.rule == "contains_moves":
            candidates = engine.get_pseudo_legal_moves(board)
            engine_uci = {m.uci() for m in candidates}
            required = set(fx.expected["required_uci"])
            missing = required - engine_uci
            passed = not missing
            detail = "ok" if passed else f"missing required moves: {sorted(missing)}"

        elif fx.rule == "excludes_moves":
            candidates = engine.get_pseudo_legal_moves(board)
            engine_uci = {m.uci() for m in candidates}
            forbidden = set(fx.expected["forbidden_uci"])
            present = forbidden & engine_uci
            passed = not present
            detail = "ok" if passed else f"engine offered forbidden moves: {sorted(present)}"

        elif fx.rule == "eval_winning":
            score = int(engine.evaluate_board(board))
            passed = score >= fx.expected["min_score"]
            detail = f"score={score} (need >= {fx.expected['min_score']})"

        elif fx.rule == "eval_losing":
            score = int(engine.evaluate_board(board))
            passed = score <= fx.expected["max_score"]
            detail = f"score={score} (need <= {fx.expected['max_score']})"

        elif fx.rule == "terminal_winner":
            outcome = board.outcome(claim_draw=True)
            expected_color = chess.WHITE if fx.expected["winner_color"] == "white" else chess.BLACK
            actual_winner = outcome.winner if outcome else None
            passed = actual_winner == expected_color
            detail = f"outcome.winner={actual_winner} expected={expected_color}"
            # Cross-check: engine eval should not contradict (non-negative for the winning side).
            if passed and board.turn == expected_color:
                score = int(engine.evaluate_board(board))
                if score < 0:
                    detail += f" (warning: engine eval={score} disagrees with terminal win)"

        elif fx.rule == "not_terminal":
            passed = not board.is_game_over(claim_draw=True)
            detail = "ok" if passed else f"board.is_game_over()=True; outcome={board.outcome(claim_draw=True)}"

        else:
            passed = False
            detail = f"unknown rule {fx.rule!r}"

    except Exception as exc:
        passed = False
        detail = f"exception: {type(exc).__name__}: {exc}"

    elapsed = time.perf_counter() - start
    return TestResult(test_id=fx.test_id, tier=tier, passed=passed, detail=detail, elapsed_s=elapsed)


def _run_tier2_fixture(engine: ModuleType, fx: Tier2Fixture, depth_override: int | None) -> TestResult:
    start = time.perf_counter()
    board = chess.variant.AntichessBoard(fx.fen)
    depth = depth_override if depth_override is not None else fx.depth
    config = SearchConfig(max_depth=depth)
    try:
        result = iterative_deepening(board, engine, config)
        chosen = result.best_move_uci
        passed = chosen in fx.expected_moves
        detail = (
            f"chose={chosen} expected_any_of={sorted(fx.expected_moves)} "
            f"depth_completed={result.depth_completed} score_cp={result.score_cp}"
        )
    except Exception as exc:
        passed = False
        detail = f"exception: {type(exc).__name__}: {exc}"
    elapsed = time.perf_counter() - start
    return TestResult(test_id=fx.test_id, tier=2, passed=passed, detail=detail, elapsed_s=elapsed)


def run_tier0(engine: ModuleType) -> list[TestResult]:
    return [_run_tier1_fixture(engine, fx, tier=0) for fx in TIER0_FIXTURES]


def run_tier1(engine: ModuleType) -> list[TestResult]:
    return [_run_tier1_fixture(engine, fx, tier=1) for fx in TIER1_FIXTURES]


def run_tier2(engine: ModuleType, depth: int | None = None) -> list[TestResult]:
    return [_run_tier2_fixture(engine, fx, depth) for fx in TIER2_FIXTURES]


def run_all(engine_name: str, depth: int | None = None) -> EngineCorrectnessReport:
    engine = load_engine(engine_name)
    t0 = run_tier0(engine)
    t1 = run_tier1(engine)
    t2 = run_tier2(engine, depth=depth)
    return EngineCorrectnessReport(
        engine_name=engine_name,
        tier0_passed=sum(1 for r in t0 if r.passed),
        tier0_total=len(t0),
        tier1_passed=sum(1 for r in t1 if r.passed),
        tier1_total=len(t1),
        tier2_passed=sum(1 for r in t2 if r.passed),
        tier2_total=len(t2),
        results=t0 + t1 + t2,
    )


def write_report_json(report: EngineCorrectnessReport) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{report.engine_name}.json"
    payload = {
        "engine_name": report.engine_name,
        "tier0_passed": report.tier0_passed,
        "tier0_total": report.tier0_total,
        "tier1_passed": report.tier1_passed,
        "tier1_total": report.tier1_total,
        "tier2_passed": report.tier2_passed,
        "tier2_total": report.tier2_total,
        "tier0_pass_rate": report.tier0_pass_rate,
        "tier1_pass_rate": report.tier1_pass_rate,
        "tier2_pass_rate": report.tier2_pass_rate,
        "results": [asdict(r) for r in report.results],
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return path


def print_human_report(report: EngineCorrectnessReport, *, verbose: bool = True) -> None:
    print(f"=== {report.engine_name} ===")
    print(f"Tier 0 (broad coverage):   {report.tier0_passed}/{report.tier0_total} "
          f"({report.tier0_pass_rate:.0%})")
    print(f"Tier 1 (rule compliance):  {report.tier1_passed}/{report.tier1_total} "
          f"({report.tier1_pass_rate:.0%})")
    print(f"Tier 2 (strategic):        {report.tier2_passed}/{report.tier2_total} "
          f"({report.tier2_pass_rate:.0%})")
    if verbose:
        for r in report.results:
            # Skip Tier 0 passes to keep the per-engine report short; show only failures + Tier 1/2.
            if r.tier == 0 and r.passed:
                continue
            flag = "PASS" if r.passed else "FAIL"
            print(f"  [{flag}] T{r.tier} {r.test_id} ({r.elapsed_s*1000:.0f}ms): {r.detail}")
    print()


def validate_fixtures() -> list[str]:
    """Sanity-check every fixture against chess.variant.AntichessBoard.

    Returns a list of error strings (empty list means all fixtures are well-formed).
    Catches: malformed FENs, expected moves that aren't actually legal at that
    position, exact-set fixtures whose expected legal_uci doesn't match the
    board, terminal fixtures whose claimed winner disagrees with python-chess.
    """
    errors: list[str] = []

    for fx in TIER0_FIXTURES:
        try:
            chess.variant.AntichessBoard(fx.fen)
        except Exception as exc:
            errors.append(f"[T0 {fx.test_id}] FEN parse error: {exc}")

    for fx in TIER1_FIXTURES:
        try:
            board = chess.variant.AntichessBoard(fx.fen)
        except Exception as exc:
            errors.append(f"[T1 {fx.test_id}] FEN parse error: {exc}")
            continue
        legal_uci = {m.uci() for m in board.legal_moves}

        if fx.rule == "legal_moves_exact":
            expected = set(fx.expected.get("legal_uci", []))
            if expected != legal_uci:
                errors.append(
                    f"[T1 {fx.test_id}] legal_moves_exact mismatch: "
                    f"fixture={sorted(expected)} board.legal_moves={sorted(legal_uci)}"
                )
        elif fx.rule == "contains_moves":
            required = set(fx.expected.get("required_uci", []))
            illegal = required - legal_uci
            if illegal:
                errors.append(
                    f"[T1 {fx.test_id}] required moves not actually legal: {sorted(illegal)}"
                )
        elif fx.rule == "excludes_moves":
            forbidden = set(fx.expected.get("forbidden_uci", []))
            present = forbidden & legal_uci
            if present:
                errors.append(
                    f"[T1 {fx.test_id}] forbidden moves are actually legal at this position "
                    f"(fixture is broken): {sorted(present)}"
                )
        elif fx.rule == "terminal_winner":
            outcome = board.outcome(claim_draw=True)
            expected_color = chess.WHITE if fx.expected["winner_color"] == "white" else chess.BLACK
            actual = outcome.winner if outcome else None
            if actual != expected_color:
                errors.append(
                    f"[T1 {fx.test_id}] terminal_winner mismatch: "
                    f"fixture expects {fx.expected['winner_color']} ({expected_color}); "
                    f"board.outcome().winner={actual}"
                )
        elif fx.rule == "not_terminal":
            if board.is_game_over(claim_draw=True):
                errors.append(
                    f"[T1 {fx.test_id}] not_terminal fixture is actually terminal: "
                    f"outcome={board.outcome(claim_draw=True)}"
                )
        elif fx.rule in ("eval_winning", "eval_losing", "move_gen_superset"):
            pass  # nothing static to validate

    for fx in TIER2_FIXTURES:
        try:
            board = chess.variant.AntichessBoard(fx.fen)
        except Exception as exc:
            errors.append(f"[T2 {fx.test_id}] FEN parse error: {exc}")
            continue
        legal_uci = {m.uci() for m in board.legal_moves}
        illegal_expected = set(fx.expected_moves) - legal_uci
        if illegal_expected:
            errors.append(
                f"[T2 {fx.test_id}] expected_moves contains illegal UCIs at this position: "
                f"{sorted(illegal_expected)}"
            )
        if not fx.expected_moves & legal_uci:
            errors.append(
                f"[T2 {fx.test_id}] no expected_move is legal -- test is unsatisfiable"
            )

    return errors


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Hidden antichess correctness suite")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--engine", help="single engine name (engines/<name>.py)")
    g.add_argument("--all", action="store_true", help="run against every engine in engines/")
    g.add_argument("--validate-fixtures", action="store_true",
                   help="check every fixture FEN/expected against python-chess and exit")
    p.add_argument("--depth", type=int, default=None,
                   help="override Tier 2 search depth (default: per-fixture)")
    p.add_argument("--json", action="store_true",
                   help="emit machine-readable JSON to stdout instead of human report")
    p.add_argument("--no-write", action="store_true",
                   help="do not write per-engine JSON to evaluation/results/correctness/")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    if getattr(args, "validate_fixtures"):
        errors = validate_fixtures()
        if errors:
            print(f"FIXTURE VALIDATION FAILED ({len(errors)} error(s)):", file=sys.stderr)
            for e in errors:
                print(f"  {e}", file=sys.stderr)
            return 1
        print(f"Fixture validation OK ({len(TIER0_FIXTURES)} Tier 0, "
              f"{len(TIER1_FIXTURES)} Tier 1, {len(TIER2_FIXTURES)} Tier 2).")
        return 0

    if args.all:
        engine_names = [n for n in list_engines() if not n.startswith("_")]
    else:
        engine_names = [args.engine]

    reports: list[EngineCorrectnessReport] = []
    for name in engine_names:
        try:
            report = run_all(name, depth=args.depth)
        except Exception as exc:
            print(f"[{name}] FAILED to run suite: {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        reports.append(report)
        if not args.no_write:
            write_report_json(report)
        if not args.json:
            print_human_report(report)

    if args.json:
        json.dump(
            [
                {
                    "engine_name": r.engine_name,
                    "tier0_pass_rate": r.tier0_pass_rate,
                    "tier1_pass_rate": r.tier1_pass_rate,
                    "tier2_pass_rate": r.tier2_pass_rate,
                    "tier0_passed": r.tier0_passed,
                    "tier0_total": r.tier0_total,
                    "tier1_passed": r.tier1_passed,
                    "tier1_total": r.tier1_total,
                    "tier2_passed": r.tier2_passed,
                    "tier2_total": r.tier2_total,
                }
                for r in reports
            ],
            sys.stdout,
            indent=2,
        )
        print()

    if args.all:
        print("=== Summary ===")
        print(f"{'engine':<40} {'T0':>10} {'T1':>10} {'T2':>10}")
        for r in reports:
            print(f"{r.engine_name:<40} "
                  f"{r.tier0_passed:>3}/{r.tier0_total:<3}    "
                  f"{r.tier1_passed:>3}/{r.tier1_total:<3}    "
                  f"{r.tier2_passed:>3}/{r.tier2_total:<3}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
