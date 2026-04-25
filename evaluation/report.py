"""Helpers for reading per-engine tokens.csv files and writing result rows."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path


ENGINES_DIR = Path("engines")


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
