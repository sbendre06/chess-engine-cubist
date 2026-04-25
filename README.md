# Cubist Antichess Ablation

This project is an ablation study of prompting strategies for AI-generated antichess engines. Each engine in `engines/` was written by a Claude session given a specific combination of three prompt ingredients — architectural guidance, antichess strategy knowledge, and opening-theory planning — while the search, UCI loop, and game rules were provided as a frozen harness the agent could not modify. The goal is to measure how much each ingredient contributes to playing strength, using win rate against a hand-written baseline engine as the primary metric and a three-tier correctness suite as a secondary diagnostic.

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

- **arch** — whether the agent was given explicit architectural guidance (e.g., which python-chess APIs to prefer, how the harness filters moves).
- **strat** — whether the agent was given antichess-specific strategy knowledge drawn from Watkins' proof (inverted material, forced-capture dynamics, capture-liability heuristics).
- **plan** — whether the agent was given opening theory or a multi-step planning phase before writing code.

| Engine | arch | strat | plan | Win rate vs baseline | Notes |
|--------|------|-------|------|---------------------|-------|
| `baseline` | — | — | — | reference | Hand-written; not AI-generated |
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

Correctness and win rate are weakly correlated. `yesarch_nostrat_noplan` (0.000 win rate) scores 12/14 on Tier 1 — it understands the rules but plays poorly. `noarch_yesstrat_noplan` (0.750 win rate) scores only 12/14 on Tier 1 but wins three quarters of its games. Rule compliance is necessary but not sufficient; the strategic heuristics in `evaluate_board` and `order_moves` drive the actual performance gap.

---

## Repo Structure

```
engines/              One Python file per ablation condition plus baseline, template, and caveman.
                      Each file exports get_pseudo_legal_moves, evaluate_board, order_moves.
                      Paired <name>.tokens.csv files record prompt cost (input/output tokens,
                      wall time, notes).

harness/              Frozen code that agents may not modify.
  engine.py           Negamax alpha-beta with iterative deepening, time control, UCI shell.
  loader.py           Dynamic importer; enforces the Core 3 contract.
  logger.py           Per-search structured logging.
  cli.py              Entry point wired from main.py.

evaluation/           Tournament and correctness infrastructure.
  adapter.py          Wraps a loaded engine module as a MoveEngine (name/choose_move/close).
  match_loop.py       Core game loop used by both tournament.py and compare.py.
  tournament.py       Runs every engine vs the baseline; writes CSV + updates experiment_log.csv.
  correctness.py      Three-tier correctness suite with CLI.
  correctness_fixtures.py  Curated FEN positions and expected results for Tiers 0–2.
  correctness_matrix.py    Renders a pass/fail table across all engines.
  correctness_plot.py      Writes a heatmap PNG.
  openings.py         Generates balanced opening FENs by random walk + reference-engine filtering.
  stochastic.py       Eval-noise wrapper to break determinism in tournament play.
  report.py           Token-cost reader, Elo utilities, experiment_log updater.
  results/            Tournament CSVs and per-engine correctness JSON (gitignored or committed
                      depending on run).

tools/
  resumable_tournament.py   Tournament runner with per-game checkpointing and resume support.
  simple_web_gui.py         Browser-based board to play manually against any engine.
  gui_vs_engine.py          Tkinter GUI variant.

docs/
  correctness_suite.md      Detailed fixture documentation for all 71 correctness tests.

legacy/               Pre-harness prototype engines and their dedicated tools; not on the
                      main ablation path.

experiment_log.csv    One row per engine: token costs, win rates, correctness pass rates.
main.py               UCI entry point: python main.py --engine <name> then pipe UCI commands.
AGENTS.md             Instructions given to each Claude session that generated an engine.
```
