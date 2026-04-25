# AGENTS.md

You are a Claude session generating an antichess engine. Stay inside the
contract below so your output is comparable to other sessions.

## 1. Your Job

Write ONE file: `engines/<yourname>.py`. It must export exactly three
callables. That is your entire surface area. Everything else (the UCI loop,
the search, time control, match running) is frozen and not yours to touch.

## 2. Branch Setup — Do This First

```
git checkout branch-template
git pull
git checkout -b agent/<yourname>
cp engines/_template.py engines/<yourname>.py
```

**Do NOT run `git merge main` or `git pull origin main` at any point.** Your
branch is deliberately missing some files; merging main would add them back
and invalidate your run. If git warns you're behind main, ignore it.

## 3. The Three Functions

Your `engines/<yourname>.py` must export:

```python
def get_pseudo_legal_moves(
    board: chess.variant.AntichessBoard,
) -> list[chess.Move]:
    ...

def evaluate_board(
    board: chess.variant.AntichessBoard,
) -> int:
    ...

def order_moves(
    board: chess.variant.AntichessBoard,
    moves: list[chess.Move],
) -> list[chess.Move]:
    ...
```

Return value semantics:

- `get_pseudo_legal_moves` — candidate moves for the current position.
- `evaluate_board` — integer score from the side-to-move perspective;
  higher means better for the side to move.
- `order_moves` — the same set of moves the harness passed in, reordered.

The harness filters the moves your `get_pseudo_legal_moves` returns
through `board.legal_moves` before playing anything.

## 4. Antichess Rules

- If any capture is legal, only captures may be played.
- A player with no legal moves WINS (stalemate is a win).
- A player with zero pieces WINS.

## 5. How to Test Your Engine

After you've filled in the three functions:

```
python main.py --engine <yourname>
```

Then paste these UCI commands, one per line:

```
uci
isready
position startpos
go depth 4
quit
```

Expect `uciok`, `readyok`, some `info` lines, then `bestmove <uci>`. If you
see `error: engines/<yourname>.py is missing required callable(s)`, one of
your three functions is named wrong or isn't at module scope.

## 6. Mandatory Cost Logging

At the end of your session, APPEND ONE ROW to
`engines/<yourname>.tokens.csv` (create the file with the header if it
doesn't exist):

```csv
prompt_name,input_tokens,output_tokens,elapsed_s,note
<yourname>,<input>,<output>,<seconds>,<note>
```

Columns:

- `prompt_name` — your assigned name (tell your team what to put here).
- `input_tokens` / `output_tokens` — from your Claude Code session summary.
- `elapsed_s` — wall-clock seconds from your first prompt to your final
  commit.
- `note` — a short tag your team will tell you to use.

Engines missing a tokens.csv are excluded from the scoring table.

## 7. Frozen Zone — Do Not Modify

- `harness/` — the UCI loop and search.
- `evaluation/` — the match runner.
- `main.py` — the CLI entrypoint.
- `engines/_template.py` — other sessions copy this too.
- Any other `engines/<other>.py` or `engines/<other>.tokens.csv`.

If your engine "needs" something outside the three functions in section 3,
the answer is to work within the contract.

## 8. Submitting

1. Commit `engines/<yourname>.py` and `engines/<yourname>.tokens.csv` on
   `agent/<yourname>`.
2. Push and open a PR targeting `main`.
3. Do not merge your own PR.
