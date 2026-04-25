"""
Optional Syzygy tablebase probing for antichess / giveaway (Person 4).

Notes:
- Use python-chess syzygy if paths provided; variant boards AntichessBoard / GiveawayBoard
  per TB compatibility with installed files.
- Probe WDL first; optional DTZ for perfect conversion metrics (engine may only need WDL).
- Fail soft: if files missing or probe error, return None and let search continue.
- Thread-safety: document if probe called from search threads.

API sketch:
- class TablebaseConfig: paths, max_pieces, variant name
- probe_wdl(board) -> optional result
- probe_dtz(board) -> optional result
"""

from __future__ import annotations


class TablebaseConfig:
    """SyzygyPath and related UCI options."""

    ...


def probe_wdl(board, config: TablebaseConfig):
    """Return None if unavailable; else WDL enum / int compatible with search."""
    ...


def probe_dtz(board, config: TablebaseConfig):
    """Optional; None if not used."""
    ...
