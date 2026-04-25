"""
Optional thin entrypoint: delegate to antiengine.uci or a future GUI.

python main.py  ->  could invoke UCI or print help.
"""

from __future__ import annotations

from antiengine.uci import main as uci_main


def main() -> None:
    """Re-export uci.main() or argparse to choose mode."""
    uci_main()


if __name__ == "__main__":
    main()
