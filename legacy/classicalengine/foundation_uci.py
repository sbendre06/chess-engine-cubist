from __future__ import annotations

import sys

from legacy.classicalengine.foundation_engine import FoundationUCIEngine


def main() -> None:
    engine = FoundationUCIEngine()
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        engine.handle_command(line)
        if engine.quit_requested:
            break


if __name__ == "__main__":
    main()
