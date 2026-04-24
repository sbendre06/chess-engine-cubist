#!/usr/bin/env python3
"""
CLI for running tuning/optimizer.py against data suites.

Usage sketch (to implement):
  python tools/tune_eval.py --suite data/test_suite.fen --method grid

Responsibilities:
- Parse CLI args: suite path, method, output log path under tuning/params_history/
- Build engine with injectable AntichessEvaluator weights
- Invoke run_optimization; print best weights for pasting into constants.py
"""

from __future__ import annotations


def main() -> None:
    """argparse / tyro entry; call tuning.optimizer.run_optimization."""
    ...
