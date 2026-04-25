# Design (boilerplate outline)

## Scope

- Greenfield antichess engine: python-chess for **rules only**; custom UCI, search, eval, TT.
- No copying Fairy-Stockfish / Sjeng / AntiCrux **implementation** code; reading for ideas allowed.

## Modules

- `antiengine/board.py` — `EngineState` wrapper.
- `antiengine/uci.py` + `antiengine/engine.py` — UCI loop and orchestration.
- `antiengine/search.py` + `antiengine/tt.py` — negamax, ID, move ordering, quiescence.
- `antiengine/eval.py` — features and weighted sum.
- `tools/match.py` — engine-vs-engine gauntlet for measurement.

## Interfaces

See `antiengine/types.py`: `SearchResult`, `SearchConfig`, `Evaluator`, `TranspositionTableProtocol`, `UCIEngine`.

## Antichess-specific search/eval notes

- Defer aggressive pruning (null, LMR, futility) until baseline validated.
- Eval: material and mobility signs inverted vs classical chess; stalemate is a **win** for the side with no moves.

