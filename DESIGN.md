# Design (boilerplate outline)

## Scope

- Greenfield antichess engine: python-chess for **rules only**; custom UCI, search, eval, TT, tuning.
- No copying Fairy-Stockfish / Sjeng / AntiCrux **implementation** code; reading for ideas allowed.

## Modules

- `antiengine/board.py` — `EngineState` wrapper.
- `antiengine/uci.py` + `antiengine/engine.py` — UCI loop and orchestration.
- `antiengine/search.py` + `antiengine/tt.py` — negamax, ID, move ordering, quiescence.
- `antiengine/eval.py` + `tuning/heuristics.py` — features and weighted sum.
- `tuning/objective.py` + `tuning/optimizer.py` + `tools/tune_eval.py` — fitness and search over weights.
- `antiengine/tablebase.py` — optional Syzygy.
- `tools/perft.py`, `tools/match.py`, `benchmarks/` — verification and measurement.

## Interfaces

See `antiengine/types.py`: `SearchResult`, `SearchConfig`, `Evaluator`, `TranspositionTableProtocol`, `UCIEngine`.

## Antichess-specific search/eval notes

- Defer aggressive pruning (null, LMR, futility) until baseline validated.
- Eval: material and mobility signs inverted vs classical chess; stalemate is a **win** for the side with no moves.

## Optimization method (TBD)

Document chosen method here: grid search, GA, Bayesian opt, SPSA, etc., and why.
