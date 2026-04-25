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
