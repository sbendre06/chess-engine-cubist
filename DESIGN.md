# Design (boilerplate outline)

## Scope

- Greenfield antichess engine: python-chess for **rules only**; custom UCI, search, eval, TT.
- No copying Fairy-Stockfish / Sjeng / AntiCrux **implementation** code; reading for ideas allowed.

## Modules

- `harness/` — frozen UCI shell + negamax search; loads `engines/<name>.py` modules.
- `engines/<name>.py` — agent-written Core 3 engine (get_pseudo_legal_moves / evaluate_board / order_moves).
- `evaluation/` — tournament runner that pairs every engine against the baseline.
- `tools/gui_vs_engine.py`, `tools/simple_web_gui.py` — manual play GUIs against any `engines/<name>.py`.
- `legacy/` — pre-harness reference engines (`antiengine/`, `classicalengine/`) and their tools (`match.py`, `play_vs_engine.py`, `simple_web_gui_classical.py`); not on the main ablation path.

## Interfaces

See `harness/loader.py` for the Core 3 engine contract that every `engines/<name>.py` must satisfy.

## Antichess-specific search/eval notes

- Defer aggressive pruning (null, LMR, futility) until baseline validated.
- Eval: material and mobility signs inverted vs classical chess; stalemate is a **win** for the side with no moves.

