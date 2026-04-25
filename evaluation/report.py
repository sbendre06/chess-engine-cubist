"""Helpers for reading per-engine tokens.csv files and writing result rows."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path


ENGINES_DIR = Path("engines")
EXPERIMENT_LOG_PATH = Path("experiment_log.csv")
CORRECTNESS_RESULTS_DIR = Path("evaluation/results/correctness")
EXPERIMENT_LOG_FIELDS = [
    "experiment_name",
    "tokens_in",
    "tokens_out",
    "wall_time_minutes",
    "interventions",
    "engine_winrate",
    "tier1_pass_rate",
    "tier2_pass_rate",
]


@dataclass(slots=True)
class TokenRow:
    prompt_name: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    elapsed_s: float = 0.0
    note: str = ""

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


def read_tokens(engine_name: str) -> TokenRow:
    """Read engines/<name>.tokens.csv. Returns an empty row if absent or empty."""
    path = ENGINES_DIR / f"{engine_name}.tokens.csv"
    if not path.exists():
        return TokenRow(prompt_name=engine_name, note="(no tokens.csv found)")
    with path.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return TokenRow(prompt_name=engine_name)
    row = rows[-1]  # last row wins if agent appended multiple
    return TokenRow(
        prompt_name=row.get("prompt_name", engine_name) or engine_name,
        input_tokens=_safe_int(row.get("input_tokens")),
        output_tokens=_safe_int(row.get("output_tokens")),
        elapsed_s=_safe_float(row.get("elapsed_s")),
        note=(row.get("note") or "").strip(),
    )


def score_to_elo(score: float) -> float | None:
    if score <= 0.0 or score >= 1.0:
        return None
    return -400.0 * math.log10((1.0 / score) - 1.0)


def elo_ci95(score: float, games: int) -> tuple[float, float] | None:
    if games <= 0:
        return None
    se = math.sqrt(max(1e-12, score * (1.0 - score)) / games)
    low_p = max(1e-6, score - 1.96 * se)
    high_p = min(1 - 1e-6, score + 1.96 * se)
    low = score_to_elo(low_p)
    high = score_to_elo(high_p)
    if low is None or high is None:
        return None
    return (low, high)


def elo_per_1k_tokens(elo: float | None, total_tokens: int) -> float | None:
    if elo is None or total_tokens <= 0:
        return None
    return elo / (total_tokens / 1000.0)


def _safe_int(value) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _safe_float(value) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def list_engines() -> list[str]:
    """Names of all engines/<name>.py, excluding __init__ and _template."""
    names = []
    for p in sorted(ENGINES_DIR.glob("*.py")):
        stem = p.stem
        if stem in ("__init__",):
            continue
        names.append(stem)
    return names


def read_correctness_pass_rates(engine_name: str) -> tuple[str, str]:
    """Return (tier1_pass_rate, tier2_pass_rate) as 4-decimal strings, or ('','') if absent."""
    path = CORRECTNESS_RESULTS_DIR / f"{engine_name}.json"
    if not path.exists():
        return ("", "")
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return ("", "")
    t1 = data.get("tier1_pass_rate")
    t2 = data.get("tier2_pass_rate")
    return (
        f"{t1:.4f}" if isinstance(t1, (int, float)) else "",
        f"{t2:.4f}" if isinstance(t2, (int, float)) else "",
    )


def update_experiment_log_winrates(name_to_winrate: dict[str, float]) -> None:
    """Update experiment_log.csv with each engine's winrate from a tournament.

    For each (engine_name, winrate) pair: if a row exists, overwrite the
    `engine_winrate` column. If not, append a new row with the winrate and
    blank build-cost fields (operator can fill those in later via
    log_experiment.py).

    Also fills tier1_pass_rate and tier2_pass_rate from
    evaluation/results/correctness/<engine>.json when present.
    """
    rows: list[dict] = []
    if EXPERIMENT_LOG_PATH.exists():
        with EXPERIMENT_LOG_PATH.open("r", newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

    # Backfill new columns on any pre-existing rows so the CSV stays well-formed.
    for r in rows:
        r.setdefault("tier1_pass_rate", "")
        r.setdefault("tier2_pass_rate", "")

    by_name = {r["experiment_name"]: r for r in rows}
    for name, winrate in name_to_winrate.items():
        wr_str = f"{winrate:.4f}"
        t1_str, t2_str = read_correctness_pass_rates(name)
        if name in by_name:
            by_name[name]["engine_winrate"] = wr_str
            if t1_str:
                by_name[name]["tier1_pass_rate"] = t1_str
            if t2_str:
                by_name[name]["tier2_pass_rate"] = t2_str
        else:
            rows.append(
                {
                    "experiment_name": name,
                    "tokens_in": "",
                    "tokens_out": "",
                    "wall_time_minutes": "",
                    "interventions": "",
                    "engine_winrate": wr_str,
                    "tier1_pass_rate": t1_str,
                    "tier2_pass_rate": t2_str,
                }
            )

    with EXPERIMENT_LOG_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPERIMENT_LOG_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
