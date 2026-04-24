# antiengine: greenfield Anti-Chess (Lichess antichess) engine on top of python-chess.
#
# Public surface (to be wired by integrator):
# - EngineState / board wrapper (board.py)
# - UCI loop (uci.py, engine.py)
# - Search + TT (search.py, tt.py)
# - Evaluation (eval.py) + tuning/* feature library
# - Optional Syzygy probing (tablebase.py)
#
# Import stable entry points here once implemented, e.g.:
# from antiengine.engine import UCIEngine
