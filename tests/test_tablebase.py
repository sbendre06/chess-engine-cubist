"""
Tablebase probing tests with missing files (graceful) and tiny mock if needed (Person 4).

Cases to cover:
- probe_wdl returns None when path empty
- If CI has no TB files, skip or xfail with reason
- Optional: fixture with minimal valid tablebase path for integration
"""

from __future__ import annotations


def test_tablebase_placeholder():
    ...