"""Cubist Frozen Harness entrypoint.

Run:
    python main.py --engine baseline

All harness logic lives in harness/. Engine logic lives in engines/<name>.py.
See AGENTS.md for the agent contract.
"""

from harness.cli import main

if __name__ == "__main__":
    main()
