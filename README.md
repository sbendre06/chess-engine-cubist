# Antichess Ablation

In quantitative finance, alpha lives where intuition ends. Just as quant firms builds niche strategies that defy market consensus, we’ve researched how to force LLMs out of their "generic" training shells.

By building an engine for **Antichess**—a variant where the goal is to lose and captures are mandatory—we created a stress test for AI. Standard LLMs are biased toward "winning" conventional chess; they struggle when the logic is inverted. This repository is an ablation study of prompting strategies used to override that bias.

Each engine in `engines/` was written by a Claude session given a specific combination of three prompt ingredients — architectural guidance, antichess strategy knowledge, and opening-theory planning — while the search, UCI loop, and game rules were provided as a frozen harness the agent could not modify.

Built for Cubist Hackathon 2026 and future experimentation.
Sohan Bendre, Casper Liao, Austin Senna Wijaya, Kevin Wu, Aiden Zhou.

---

## The Research Framework

Because we had limited credits to run our experiments, we divided our research framework into two parts: **Evaluation Framework** and **Parallel Subagents**.

### 0. Deep Research & The Baseline
Before running the ablation, we established a **Gold Standard Baseline**. This was not hand-written, but generated through a high-resource "Deep Research" workflow:
* **Gemini Pro (Student Plan):** Used to perform deep research over existing engines and the Watkins strategy paper.
* **Opus 4.6:** Used the summarized research context to brainstorm, plan, and implement the baseline via incremental commits and code-review critique agents.
* **Standardization:** We used this process to build the **Engine Infrastructure**, creating a template branch with stubs (`evaluate_board`, `get_pseudo_legal_moves`, `order_moves`) so that parallel subagents could be tested cheaply and without information leakage.

---

## The Harness Interface Contract

Every engine must export exactly three callables. The harness loader (`harness/loader.py:8`) enforces this at import time and raises `EngineContractError` if any are missing.

```python
def get_pseudo_legal_moves(board: chess.variant.AntichessBoard) -> list[chess.Move]:
    ...

def evaluate_board(board: chess.variant.AntichessBoard) -> int:
    ...

def order_moves(board: chess.variant.AntichessBoard, moves: list[chess.Move]) -> list[chess.Move]:
    ...
```

**`get_pseudo_legal_moves`** — returns candidate moves for the current position. The harness filters this list through `board.legal_moves` before any move is played, so the engine cannot play an illegal move, but it can starve the search by omitting legal moves.

**`evaluate_board`** — returns an integer score from the side-to-move perspective (negamax convention: higher is better for whoever is to move). The harness owns terminal scoring; this function is called only at non-terminal leaf nodes and depth-0 cutoffs. Antichess inverts standard material signs: fewer of your own pieces is better.

**`order_moves`** — takes the filtered legal move list and returns it in a preferred order. Called at every node in the alpha-beta tree. Better ordering earlier means more beta cutoffs and effectively deeper search.

This split exists so the search algorithm, time control, and UCI protocol can be held constant across all experimental conditions. The only variable is the engine module — a clean single-file intervention surface with no shared state.

---

## Running the Tournament Pipeline

Prerequisites: Python 3.11+, `python-chess` installed (see `requirements.txt` or `pyproject.toml`).

**Run all engines against the baseline:**

```bash
python -m evaluation.tournament --baseline baseline --games 20 --depth 3
```

Key options:

| Flag | Default | Description |
|------|---------|-------------|
| `--baseline` | `baseline` | Name of the reference engine (`engines/<name>.py`) |
| `--games` | 20 | Games per matchup (played in color-alternating pairs) |
| `--depth` | 3 | Max search depth for iterative deepening |
| `--movetime-ms` | None | Per-move time limit in ms (overrides depth) |
| `--noise-cp` | 3 | ±cp uniform jitter on `evaluate_board` to break determinism |
| `--opening-plies` | 4 | Random plies from start to build each opening FEN |
| `--balance-threshold` | 200 | Reject openings where `|baseline_eval_cp| >` this value |
| `--seed` | random | RNG seed for openings and eval noise |
| `--skip` | `_template` | Engine names to exclude; pass multiple times |

Results are written to `evaluation/results/tournament-<timestamp>.csv` and win rates are merged back into `experiment_log.csv`.

**Resumable tournament** (survives interruption, per-game checkpointing):

```bash
python tools/resumable_tournament.py --games 20 --depth 3
python tools/resumable_tournament.py --resume evaluation/results/tournament-resumable-<timestamp>.state.json
python tools/resumable_tournament.py --games 20 --depth 3 --only caveman
```

**Manual play against any engine:**

```bash
python tools/simple_web_gui.py --engine yesarch_yesstrat_yesplan_p1
```

---

## Running the Correctness Suite

The suite has three tiers:

- **Tier 0** (50 fixtures): broad coverage — random-walk positions; asserts the engine's filtered pseudo-legal output is a superset of `board.legal_moves`.
- **Tier 1** (14 fixtures): targeted rule compliance — hand-curated antichess edge cases (forced capture, no castling, king-capturable, promotion-to-king, stalemate-as-win, inverted material signs, etc.).
- **Tier 2** (7 fixtures): strategic decision quality — drives `iterative_deepening` at fixed depth on Watkins-derived positions and checks the chosen root move against an accepted set.

```bash
# Single engine
python -m evaluation.correctness --engine baseline

# All engines
python -m evaluation.correctness --all

# Override Tier 2 search depth
python -m evaluation.correctness --all --depth 4

# Machine-readable JSON to stdout (per-engine files still written)
python -m evaluation.correctness --all --json

# Skip writing per-engine JSON files
python -m evaluation.correctness --engine baseline --no-write

# Validate every fixture FEN and expected-move set against python-chess
python -m evaluation.correctness --validate-fixtures

# Rendered pass/fail table across all engines
python -m evaluation.correctness_matrix

# Heatmap PNG (evaluation/results/correctness_matrix.png)
python -m evaluation.correctness_plot
```

Per-engine results land in `evaluation/results/correctness/<engine>.json`. After a tournament run, `tier0_pass_rate`, `tier1_pass_rate`, and `tier2_pass_rate` are merged into `experiment_log.csv`.

---

## Ablation Conditions

The three prompt axes are:

- **arch** — explicit architectural guidance (APIs, harness constraints).
- **strat** — antichess-specific strategy knowledge drawn from Watkins' paper (500-word condensed summary).
- **plan** — Multi-step planning phase (Elite AI Researcher & Senior SE persona) vs. one-shotting.

| Engine | arch | strat | plan | Win rate vs baseline | Notes |
|--------|------|-------|------|---------------------|-------|
| `baseline` | — | — | — | reference | **Deep-Research iterative engine** |
| `caveman` | no | no | no | 0.000 | Primitive naive implementation |
| `noarch_nostrat_noplan` | no | no | no | 0.000 | Full ablation (no ingredients) |
| `noarch_nostrat_yesplan` | no | no | yes | 0.500 | Planning alone breaks even |
| `noarch_yesstrat_noplan` | no | yes | no | 0.750 | Best single-ingredient result |
| `arch1-strat1-plan1` | yes | yes | yes | 0.500 | Earlier prompt iteration of all-three |
| `yesarch_nostrat_noplan` | yes | no | no | 0.000 | Arch alone does not help |
| `yesarch-nostrat-yesplan` | yes | no | yes | 0.250 | Arch + plan without strategy hurts |
| `yesarch_yessttrat_noplan` | yes | yes | no | 0.500 | Arch + strategy without planning |
| `yesarch_yesstrat_yesplan_p1` | yes | yes | yes | 1.000 | All three; best result |

Win rates are score against the baseline (0.5 = even; 1.0 = won every game).

---

## Key Results

`yesarch_yesstrat_yesplan_p1` is the strongest condition, winning all games against the baseline (1.000 score). It also achieves 13/14 on Tier 1 correctness and 4/7 on Tier 2 strategy tests.

The most informative comparison is between `noarch_yesstrat_noplan` (0.750) and `yesarch_nostrat_noplan` (0.000): antichess domain knowledge (strategy) contributes far more to playing strength than structural coding guidance (architecture) when used in isolation. Architecture guidance without strategy does not improve over the full ablation. Planning alone (`noarch_nostrat_yesplan`, 0.500) is enough to match the baseline but not beat it. The full combination of all three ingredients achieves the ceiling.

---

## Extensions

With more resources such as Claude max, we could spawn more parallel subagents to enhance sample sizes to solidify significance in our findings and move toward an iterative "Natural Selection" improvement of the winning configurations.

---

## Repo Structure

```
engines/              One Python file per ablation condition plus baseline, template, and caveman.
                      Each file exports get_pseudo_legal_moves, evaluate_board, order_moves.
                      Paired <name>.tokens.csv files record prompt cost.

harness/              Frozen code that agents may not modify.
  engine.py           Negamax alpha-beta with iterative deepening, time control, UCI shell.
  loader.py           Dynamic importer; enforces the Core 3 contract.
  logger.py           Per-search structured logging.
  cli.py              Entry point wired from main.py.

evaluation/           Tournament and correctness infrastructure.
  adapter.py          Wraps a loaded engine module as a MoveEngine.
  match_loop.py       Core game loop used by tournament.py.
  tournament.py       Runs every engine vs the baseline; writes CSV.
  correctness.py      Three-tier correctness suite with CLI.
  correctness_fixtures.py  Curated FEN positions and expected results.
  correctness_matrix.py    Renders a pass/fail table across all engines.
  correctness_plot.py      Writes a heatmap PNG.
  openings.py         Generates balanced opening FENs.
  stochastic.py       Eval-noise wrapper to break determinism.
  report.py           Token-cost reader and ELO utilities.
  results/            Tournament CSVs and per-engine correctness JSON.

tools/
  resumable_tournament.py   Tournament runner with checkpointing.
  simple_web_gui.py         Browser-based board to play manually.
  gui_vs_engine.py          Tkinter GUI variant.

docs/
  correctness_suite.md      Detailed fixture documentation for all 71 tests.

experiment_log.csv    One row per engine: token costs, win rates, correctness pass rates.
main.py               UCI entry point: python main.py --engine <name>.
AGENTS.md             Instructions given to each Claude session.
```
