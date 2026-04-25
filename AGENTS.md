# AGENTS.md — Ablation Branch Instructions

You are one of several Claude sessions generating an antichess engine for a
prompt-ablation study. Each agent gets a different prompt; the engine code
you produce is the dependent variable. Stay in your lane so the experiment
stays valid.

## 1. Your Job

Write ONE file: `engines/<yourname>.py`. It must export exactly three
callables. That is your entire surface area. Everything else (UCI protocol,
search, time control, evaluation tournaments) is frozen and not yours to
touch.

## 2. Branch Setup — Do This First

```
git checkout branch-template
git pull
git checkout -b agent/<yourname>
cp engines/_template.py engines/<yourname>.py
```

**Do NOT run `git merge main` or `git pull origin main` at any point.**
`branch-template` is deliberately missing the reference baseline
(`engines/baseline.py`); merging main would leak it into your working copy
and contaminate the experiment. If git complains about being behind main,
ignore it — you are branched from `branch-template` on purpose.

## 3. The Three Functions

```python
import chess
import chess.variant

def get_pseudo_legal_moves(
    board: chess.variant.AntichessBoard,
) -> list[chess.Move]:
    """Return candidate moves. MUST enforce antichess's forced-capture rule:
    if any pseudo-legal capture exists, only captures may be returned.
    Returned moves need not all be fully legal; the harness filters through
    board.legal_moves before playing anything."""

def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    """Static heuristic score in centipawns, from the side-to-move
    perspective. Higher = better for whoever is to move. Called at leaf
    nodes of search."""

def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    """Reorder `moves` best-first so alpha-beta gets early cutoffs. Must
    return the same set of moves, just reordered — no additions, no drops."""
```

## 4. Antichess Rules Crib

- **Forced captures:** If you have any legal capture, you MUST play a
  capture. Non-capture moves are illegal in that position.
- **Stalemate is a WIN** for the side with no legal moves (opposite of
  classical chess).
- **Bare-pieces win:** A side with zero pieces WINS (they've achieved the
  goal).
- **Inverted signs in eval:** Fewer own pieces is better. Fewer own legal
  moves is better. More opponent mobility is better. This is the opposite
  of classical chess.

## 5. How to Test Your Engine

```
python main.py --engine <yourname>
```

Then paste these UCI commands one per line:
```
uci
isready
position startpos
go depth 4
quit
```

Expect `uciok`, `readyok`, info lines, then `bestmove <uci>`. If you get
`error: engines/<yourname>.py is missing required callable(s)` instead,
your file doesn't export one of the Core 3.

## 6. Mandatory Cost Logging

At the end of your Claude Code session, APPEND ONE ROW to
`engines/<yourname>.tokens.csv` (create the file if it doesn't exist) with
this exact header and one data row:

```csv
prompt_name,input_tokens,output_tokens,elapsed_s,note
<yourname>,<input>,<output>,<seconds>,<components>
```

Columns:
- `prompt_name`: your ablation branch name (e.g. `kitchen_sink`,
  `no_persona`, `no_strategy`, `no_architecture`, `control`).
- `input_tokens` / `output_tokens`: from your Claude Code session summary.
- `elapsed_s`: wall-clock seconds from your first prompt to your final
  commit.
- `note`: the components your prompt contained, like `C+S+A+P` (see the
  study design in `context.txt`).

This CSV is how the evaluation tournament assigns "cost" to your engine
for the Elo-per-token analysis. Without it, your engine is excluded from
the ablation table.

## 7. Frozen Zone — Do Not Modify

You MUST NOT modify any of:
- `harness/` — the UCI loop and search. Shared across all engines.
- `evaluation/` — the tournament runner.
- `main.py` — the CLI entrypoint.
- `engines/_template.py` — other agents copy this too.
- Any other `engines/<other>.py` or `engines/<other>.tokens.csv`.
- `tools/match.py` — the older antiengine gauntlet.
- `antiengine/`, `classicalengine/` — prior-art reference code.

If your engine "needs" something outside the Core 3, the answer is to work
within the contract. The harness intentionally constrains you.

## 8. Submitting

1. Commit your engine file and your tokens.csv on `agent/<yourname>`.
2. Push and open a PR targeting `main`.
3. **Do not merge your own PR.** The Librarian merges all agent PRs in one
   batch after the build window closes. Merging early would leak baseline
   code into other agents' branches if they rebase.
