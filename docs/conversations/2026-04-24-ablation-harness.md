# 2026-04-24 — Ablation-ready harness refactor

## Request

Restructure the repo so each prompt-ablation branch produces ONE file
(`engines/<name>.py`) implementing a tight foundation API, with shared
harness code frozen, an evaluation module to pit engines head-to-head, a
fixed baseline as reference, and tokens/time logged per agent.

## Key decisions

- **Core 3 API**, not 4. `terminal_score` was dropped from the agent
  surface because it's rules, not strategy — every correct engine
  returns the same sign at terminal nodes, so leaving it to agents just
  invites bugs without generating ablation signal. Harness owns it via
  `board.outcome()`.
- **Three-branch model** so agents never see the reference baseline:
  - `main` — full state including `engines/baseline.py`
  - `branch-template` — `main` minus baseline; where agents start
  - `agent/<name>` — branched from branch-template, adds one file
  Agents are told NOT to merge main into their branch.
- **Layout flat**: `engines/<name>.py` + `engines/<name>.tokens.csv`
  sitting next to each other. Single file per engine, easy to diff.
- **Token logging** is build-time, not runtime. Each agent writes one row
  to their tokens.csv at session end. The old `ExperimentLogger` lost its
  token columns; kept its perf columns in `harness/logger.py`.

## What landed

- `harness/{engine,logger,loader,cli}.py` — frozen UCI + search, loader
  validates Core 3, CLI parses `--engine <name>`.
- `engines/baseline.py` + `engines/_template.py` with matching
  `.tokens.csv` files.
- `evaluation/{adapter,match_loop,compare,tournament,report}.py` —
  HarnessAdapter wraps a loaded engine module; match_loop takes pre-built
  adapters (so `tools/match.py` stayed untouched); compare does
  head-to-head; tournament runs every engine vs baseline and emits an
  ablation CSV + console table with Elo, CI95, and Elo/1k-tokens.
- `AGENTS.md` with the contract, branch setup, rules crib, and logging.
- `main.py` shrunk to a 2-line shim importing `harness.cli.main`.

## Verification

- `python main.py --engine baseline` runs through depth 3 and returns a
  reasonable move.
- `python main.py --engine _template` runs and returns a (weak) legal
  move — template bodies are intentionally trivial.
- Loader emits a clear error naming missing callables when an engine
  lacks one of the Core 3.
- `python -m evaluation.compare --a baseline --b _template --games 4`
  — baseline swept 4-0 as expected.
- `python -m evaluation.tournament` — writes a timestamped CSV and prints
  the ablation table.
- `pytest tests/` — 5/5 passing. `tools/match.py` still runs (untouched).
- `branch-template:engines/` contains only `__init__.py` and
  `_template.py` — baseline correctly absent.

## Branches

- `main` — 4 ahead of origin, includes this refactor.
- `branch-template` — 1 ahead of main (the baseline deletion commit).

Neither has been pushed. User can push both when ready.

## Out of scope (intentional)

- No actual ablation-branch engines built — those come from per-agent
  Claude sessions.
- No tournament run on real engines — that's for Saturday morning.
- No transposition table added to the harness (current behavior
  matched the old main.py).
- No refactor of `antiengine/`, `classicalengine/`, or the prior tests.

## Round 2: ablation-purity cleanup

After the initial landing, user flagged two contamination risks:

1. The `_template.py` docstring and AGENTS.md "rules crib" were handing
   agents Strategy content ("material and mobility signs are INVERTED")
   through the shared starter kit — meaning the "no strategy" ablation
   variant wasn't actually no-strategy; strategy was leaking via the
   template.
2. `branch-template` still carried `antiengine/`, `classicalengine/`,
   `benchmarks/`, `tests/`, `tools/`, `tuning/`, `docs/`, `context.txt`,
   `parsed_slides.txt`, `DESIGN.md`, `ROADMAP.md`, and the full
   `data/`. Agents branching from it could read the prior working
   engines for free strategic signal.

Fixes:

- `engines/_template.py` reduced to pure signatures + `raise NotImplementedError`.
  No docstrings, no bodies, no forced-capture hint.
- `AGENTS.md` rules section trimmed to the three actual rules
  (forced captures, stalemate-wins, bare-pieces-wins). Removed the
  "inverted signs" bullet and the `context.txt` reference.
- `harness/engine.py` lost its unused `PIECE_VALUES` constant — was dead
  code that would have leaked classical piece values to anyone reading
  the harness.
- `branch-template` was deleted locally and recreated from updated main,
  then had all prior-art, reference data, and study-design files `git
  rm`'d in one commit. Final tree: `.gitignore`, `AGENTS.md`,
  `README.md`, `engines/{__init__,_template}.{py,tokens.csv}`,
  `evaluation/`, `harness/`, `main.py`. That's it.
- A stale tracked `__pycache__/main.cpython-313.pyc` was removed from
  branch-template in a follow-up commit.

## Verification after round 2

- `main.py --engine baseline` still completes a depth-3 search and
  returns `bestmove g2g3`.
- `main.py --engine _template` raises `NotImplementedError` from a
  background thread after `uciok` — intentional; agents must copy and
  implement before the harness will run.
- `evaluation/compare` and `evaluation/tournament` both still run
  end-to-end (verified with `baseline` vs `baseline` and `baseline` vs
  a disposable dummy engine).
- `branch-template` simulation: copied `_template.py` → `test_agent.py`
  with three trivial bodies and a `tokens.csv`, ran UCI → reached
  `bestmove h2h3` at depth 3. Agent workflow is validated.

## Final branches

- `main` (5 ahead of origin): full repo including baseline.
- `branch-template` (2 ahead of main, via
  `aec19b1` + `1d9eaa5`): starter kit only. Agents branch from here.

Neither has been pushed. User can push both when ready.
