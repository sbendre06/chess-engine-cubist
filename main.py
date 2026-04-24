"""
Optional thin entrypoint: delegate to antiengine.uci or a future GUI.

python main.py  ->  could invoke UCI or print help.
"""

from __future__ import annotations


def main() -> None:
    """Re-export uci.main() or argparse to choose mode."""
    ...
