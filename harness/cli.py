"""CLI entrypoint: `python main.py --engine <name>` drives the UCI loop."""

from __future__ import annotations

import argparse
import sys

from harness.engine import FrozenUCIEngine
from harness.loader import EngineContractError, load_engine


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cubist Frozen Harness: loads engines/<name>.py and runs a UCI loop.",
    )
    parser.add_argument(
        "--engine",
        default="baseline",
        help="Engine module name under engines/ (default: baseline).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    try:
        engine_module = load_engine(args.engine)
    except EngineContractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

    engine = FrozenUCIEngine(engine_module, engine_name=args.engine)
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        engine.handle_command(line)
        if engine.quit_requested:
            break
