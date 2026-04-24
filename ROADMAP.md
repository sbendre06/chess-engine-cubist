# Roadmap (milestones without calendar)

1. **MVP** — Legal antichess gen + static eval + depth-limited alpha-beta + UCI `go depth`; `python -m antiengine.uci` works in a GUI.
2. **Search** — Iterative deepening, TT, ordering, info lines, time limits, quiescence for forced captures.
3. **Strength** — Richer eval features, tactic suite, `tools/tune_eval.py` weight search, perft regression.
4. **Polish** — Optional Syzygy, `tools/match.py`, benchmarks, CI, README demo.

Track issues per workstream (rules, search, eval, TB/bench, integrator) as in project plan.
