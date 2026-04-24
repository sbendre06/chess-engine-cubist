# Antichess Engine — Cubist Hackathon Design Spec

**Date:** 2026-04-24
**Event:** Cubist Hackathon, Fri 5pm – Sat 3pm (~17 working hours)
**Team:** 5 students, all Python-comfortable, none with prior chess-engine experience
**Variant:** Antichess (via `chess.variant.AntichessBoard`)
**Strategic frame:** AI-as-co-engineer, anchored by a competent baseline engine

---

## 1. Goal & judging alignment

Build an antichess engine whose *distinguishing artifact* is not raw playing strength but a **structured, parallel experimentation platform** in which each teammate uses their own Claude Pro subscription to propose, test, and refine engine variants against each other.

The Cubist rubric has four axes. This design targets them as follows:

| Axis | How this design scores |
|---|---|
| **Chess Engine Quality** | A solid alpha-beta + quiescence baseline that plays legal antichess and beats trivial opponents, improved over the weekend by experiment wins. |
| **AI Usage** | The central artifact. Every engine variant is a hypothesis proposed with Claude; the results notebook tells the story of what Claude suggested, what worked, and what surprised us. The rubric explicitly name-checks "pitting two AI-generated engines against each other" — this design makes that the core loop. |
| **Process & Parallelization** | 5 teammates × 5 independent Claude subs run concurrent experiments in separate branches. The harness serializes their results into a single Elo ladder. |
| **Engineering Quality** | Tests on eval invariants and forced-capture legality, a reproducible tournament runner, a CI smoke-test for submitted engines, documented architecture, and a results notebook. |

## 2. Why antichess

- Forced-capture rule drops branching factor to often 1–3 per ply. Alpha-beta reaches deep plies on modest hardware — a massive advantage over standard chess at a 17-hour budget.
- Eval is counter-intuitive (material is negative; mobility is roughly inverted). Claude's default chess intuition is often *wrong*, which creates a genuine AI-usage story about critically evaluating AI output.
- `chess.variant.AntichessBoard` in python-chess handles move generation, legality, stalemate-wins, and PGN I/O — we rely on it for correctness.
- Stockfish does not play antichess natively, so the comparator is Fairy-Stockfish (optional) or our own engine lineage. The "beat Stockfish" bar is replaced with a clearer internal story.

## 3. Architecture

Five components, minimal surface area:

### 3.1. `Engine` protocol

```python
class Engine:
    name: str           # identifier in tournament results
    description: str    # the hypothesis this engine tests
    def play(self, board: AntichessBoard, time_limit_s: float) -> chess.Move: ...
```

No UCI, no async, no configuration layer. Anything respecting this signature is a valid engine. UCI is added only at demo time as a thin wrapper around the winning engine.

### 3.2. `BaselineEngine`

Owner: one person (~200–300 LoC).

- **Iterative deepening** alpha-beta (gives time control for free).
- **Transposition table** keyed on `chess.polyglot.zobrist_hash(board)`.
- **Move ordering:** TT-move first, MVV-LVA on captures; killer moves is a stretch goal.
- **Quiescence:** exploits the forced-capture rule — "quiet" = "no legal captures". QS recurses while captures exist.
- **Terminal detection:** delegated to `board.is_variant_end()` / `board.result()`.
- **Baseline eval (deliberately naive, intended to be beaten):**
  - Material (inverted sign): Q=9, R=5, B=3, N=3, P=1
  - Mobility: `+0.1 × (opp_legal_moves − own_legal_moves)`
  - Captureability: `+0.05` per own piece attacked by opponent

The baseline eval is a *first draft*. Experiments that beat it become the headline AI-usage story.

### 3.3. Match harness (`harness/match.py`)

```python
def play_match(white: Engine, black: Engine, time_per_move: float,
               max_plies: int = 300) -> GameResult
```

- Forfeits on illegal move or >1.5× time overrun (prevents one broken engine from tanking a tournament).
- Max-plies cap to bound pathological draws.
- Returns `GameResult(outcome, pgn, moves, times)` for storage.

### 3.4. Tournament runner (`harness/tournament.py`)

- Reads `engines/registry.py` (dict: `name → Engine factory`).
- Round-robin across all registered engines; each pair plays `n_games` (default 20), colors alternated.
- `multiprocessing.Pool` over CPU cores.
- Writes every game to `results.db` (SQLite) and PGN to `games/`.
- Target runtime: ~8 minutes for 10 engines × 20 games on a 10-core laptop at 0.5s/move.

**Schema (SQLite):**
```sql
CREATE TABLE games (
  id INTEGER PRIMARY KEY,
  tournament_id TEXT,
  white TEXT, black TEXT,
  result TEXT,              -- '1-0', '0-1', '1/2-1/2', 'forfeit_w', 'forfeit_b'
  n_plies INTEGER,
  total_time_w REAL, total_time_b REAL,
  pgn TEXT,
  started_at REAL
);
CREATE TABLE engines (
  name TEXT PRIMARY KEY,
  description TEXT,
  commit_sha TEXT,
  parent_of TEXT            -- lineage: which engine was this derived from
);
```

### 3.5. Stats layer (`harness/stats.py`)

- Per-engine W/D/L, score %, Wilson 95% CI.
- Head-to-head matrix.
- **Bayes-Elo** via MLE fit over logistic outcomes (scipy.optimize, ~30 LoC) with error bars.
- "Upset detector": pairs whose observed win rate is >2σ off the Elo prediction — candidate games to investigate.

### 3.6. Results notebook (`results.ipynb`)

The AI-usage artifact. Auto-generated from `results.db` plus engine module docstrings.

Sections:
1. Experiment timeline: what Claude proposed → which hypotheses won/lost → what we learned about antichess.
2. Elo ladder with CIs.
3. Head-to-head matrix.
4. Surprise findings: counter-intuitive wins, with game PGN embedded.
5. Cost breakdown: tokens per experiment, cost per Elo point gained.

## 4. Experimentation workflow

Teammate writes `engines/<name>.py` with a module docstring stating the hypothesis →
opens PR → GitHub Actions runs a 10-game smoke match vs. `BaselineEngine` (correctness: does it finish games, play legal moves, respect time budget?) →
merge to `main` → included in the next full tournament →
notebook auto-refreshes.

**Two extension patterns:**

1. **Eval swap** (expected 90% of experiments): `class MyEval(BaselineEngine): def eval(self, board): ...` — one file, ~30 LoC.
2. **Wholesale engine** (the bold variants): implement `.play()` from scratch. Examples that align with the AI-usage story:
   - MCTS-based.
   - Opening-book-driven (hand-curated 1.e3 lines from lichess analysis).
   - Stochastic / epsilon-greedy with a baseline backbone.
   - **LLM-in-the-loop**: Claude Haiku as a fallback move-picker in positions flagged "uncertain" by the baseline — explicitly accounts for cost per game so the cost-efficiency criterion is not blown.

## 5. Team roles & timeline

### Roles

| Role | Owner | Primary deliverable |
|---|---|---|
| R1. Harness & infra | Person A | `match.py`, `tournament.py`, SQLite schema, CI smoke test, repo scaffolding |
| R2. Baseline engine | Person B | `BaselineEngine` + `engines/baseline.py` |
| R3. Experimenters | C, D, E | Eval-swap and wholesale engine variants, each driving their own Claude sub |
| R4. Stats & notebook | Person A (shared) | `stats.py`, `results.ipynb`, Elo ladder, commentary |
| R5. Demo & UCI wrapper | Person B (last 2h) | UCI shim, 5-min live demo, optional Lichess bot account |

Pair up for handoffs so no single-person SPOF stalls the build.

### 17-hour timeline

| Block | Time | Milestone |
|---|---|---|
| Fri 5–7pm | 2h | Repo + `Engine` protocol + `AntichessBoard` smoke test + empty `registry.py`. B starts alpha-beta. A starts harness. C/D/E read python-chess docs + sketch hypotheses in `docs/hypotheses/`. |
| Fri 7–9pm | 2h | Baseline plays legal games (even if weak). Harness runs a 2-engine match end-to-end. |
| Fri 9–11pm | 2h | **Milestone: first tournament runs.** Baseline vs. RandomMover vs. GreedyCapturer. Results in SQLite, notebook renders. C/D/E submit first eval variants. |
| Sat 11am–12pm | 1h | Triage Friday results. Claude-driven iteration: "look at games Variant-X lost, propose fixes." |
| Sat 12–2pm | 2h | Second tournament. Wholesale variants arrive (MCTS / book / Haiku-fallback). Elo ladder stabilizes. |
| Sat 2–2:30pm | 30min | **Freeze merges.** Final tournament (50 games/pair) runs in background. |
| Sat 2:30–3pm | 30min | UCI wrapper on winning engine. Rehearse demo. Notebook cleanup. Repo public. |

Each teammate drives their own Claude Pro sub in their own branch. Persons A and B support via PR review. This is the explicit parallelization story for the Process rubric axis.

## 6. Deliverables

1. **Public GitHub repo** — README, architecture doc, quickstart (`pip install -e . && python -m harness.demo`), MIT license.
2. **`engines/`** — every engine has a docstring with its hypothesis and a link to the PR where it was designed with Claude (AI-usage evidence).
3. **`results.ipynb`** — the AI-usage artifact (see §3.6).
4. **`tests/`** — eval invariants (stalemate detection, forced-capture legality), deterministic tournament reproduction with fixed seeds, UCI round-trip.
5. **Live demo** (3–5 min):
   - Terminal board view or Lichess bot account playing a judge.
   - Walk through 2–3 notebook "aha" moments.
   - PR history as the AI-usage timeline.

## 7. Explicit non-goals (YAGNI)

- No web UI.
- No distributed/cloud cluster — local multiprocessing only.
- No neural-net training pipeline (the time-risk is not worth it at 17h).
- No UCI layer during development — only as the final demo wrapper.
- No attempt to match Fairy-Stockfish strength; the Elo ladder is internal to our engine pool. A benchmark match vs. Fairy-Stockfish is a stretch goal if time permits.

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Baseline engine isn't ready by Fri 9pm → experimenters blocked | Day 1 milestone is a *legal* baseline, not a strong one. A legal engine is 100 LoC. Strength improves via the experiment loop. |
| Someone's engine has bugs (illegal moves, infinite loops) | CI smoke-test before merge; harness forfeits on illegal/timeout. |
| Tournament takes too long to iterate | Start at 10 games/pair at 0.3s/move on Friday, scale to 50 games/pair at 1.0s/move for the final run. |
| "Meta-project" feeling — engine plays badly and judges discount it | Insist on ≥1 engine in the final pool that beats a random-mover and a greedy-capturer by >80%. The baseline alone should clear this. |
| Cost blowup from LLM-in-loop engines | Use Claude Haiku (not Sonnet/Opus) for in-loop calls; cap calls per game; include cost-per-Elo in the notebook. |
| UCI integration breaks at the last hour | UCI wrapper is <100 LoC around the `.play()` method; Person B tests it against a Lichess bot during the Sat 2:30pm window *only after* the tournament is frozen. |

## 9. Success criteria

- At least 6 engine variants in the final tournament, each with a documented hypothesis.
- The Elo spread between worst and best is ≥200 points (evidence that experiments produced real improvements).
- At least one "surprise finding" — a Claude-suggested eval that beat a human-intuitive eval — documented in the notebook.
- The repo builds from a clean clone in under 5 minutes.
- The demo shows the engine playing a complete antichess game from start to finish.
