# classicalengine

Standard chess engine foundation (separate from `antiengine`).

## Run as UCI engine

```bash
.venv/bin/python -m classicalengine.uci
```

Supported commands include:
- `uci`, `isready`, `ucinewgame`
- `position startpos [moves ...]`
- `position fen ... [moves ...]`
- `go depth N`
- `go movetime T`
- `go wtime WT btime BT [winc WI] [binc BI] [movestogo M]`
- `stop`, `quit`

## Baseline strength features

- Iterative deepening + fail-soft alpha-beta
- Transposition table (hash option)
- Move ordering: TT move, tactical ordering (MVV-LVA), killer/history
- Quiescence search over captures/promotions/check evasions
- Evaluation: material + piece-square tables + mobility

## Central engine functions

`classicalengine/core.py` exposes central primitives used by search:
- `evaluate_board(board, evaluator)`
- `get_legal_moves(board)`
- `get_pseudo_legal_moves(board)`
- `make_move(board, move)` / `unmake_move(board)`
- `terminal_score(board, ply)`
- `board_key(board)`

## Agent-experiment baseline (delete/reimplement friendly)

For "same task, different coding agent" experiments, use:
- `classicalengine/foundation_model.py` (central methods to rewrite)
- `classicalengine/foundation_search.py` (minimal alpha-beta loop)
- `classicalengine/foundation_engine.py` + `classicalengine/foundation_uci.py`

Run:

```bash
.venv/bin/python -m classicalengine.foundation_uci
```

Key methods intended for experimentation in one place:
- `evaluate_board()`
- `get_legal_moves()`
- `get_pseudo_legal_moves()`
- `order_moves()`
- `make_move()` / `unmake_move()`
- `terminal_score()`
- `board_key()`
