from __future__ import annotations

import sys

from classicalengine.engine import UCIEngine


def main() -> None:
    engine = UCIEngine()
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        engine.handle_command(line)
        if engine.quit_requested:
            break


if __name__ == "__main__":
    main()
