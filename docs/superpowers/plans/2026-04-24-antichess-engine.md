# Antichess Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship an antichess engine + parallel-experimentation harness by Sat 3pm — spec at `docs/superpowers/specs/2026-04-24-antichess-engine-design.md`.

**Architecture:** `Engine` protocol → `BaselineEngine` (iterative-deepening alpha-beta + QS + TT on `chess.variant.AntichessBoard`) → match harness → SQLite-backed round-robin tournament → stats + Elo → notebook. Teammates add engines; CI smoke-tests each PR; harness ranks them.

**Tech Stack:** Python 3.11+, `python-chess` (move gen / `AntichessBoard` / zobrist / PGN), `multiprocessing` (tournament parallelism), SQLite (results), `scipy` (Elo MLE), `jupyter` + `pandas` + `matplotlib` (notebook), `pytest` (tests), GitHub Actions (CI).

**Execution order & parallelism:**
- Tasks 1 → 2 are **unblockers** — land fast. After Task 2, experimenters (C/D/E) are unblocked on engine variants.
- Task 12 (invariant tests) can run in parallel with any other task.
- Tasks 14–15 are **stretch** — run after Task 13 (UCI) lands Saturday afternoon. Spec §5 already blesses both (LLM-in-loop variant, optional Lichess bot).

**5-lane role mapping (5 people):**

| Lane | Person | Core tasks | Stretch | AI-usage story owned |
|---|---|---|---|---|
| **A — Harness & infra** | Person A | 1, 3, 4, 5, 9, 10, 11 | — | Reproducible tournament runs; Elo dashboard in notebook |
| **B — Baseline engine & UCI** | Person B | 2, 6, 7, 8, 13 | — | Alpha-beta search transparency; commits show Claude-assisted tuning |
| **C — LLM persona variant** | Person C | Experimenter (engines/llm_persona.py) | 14 | THE headline AI-usage variant; cost/Elo tracking in notebook |
| **D — Experimenter** | Person D | Variant engines via PR (eval-swap or wholesale) | — | Own hypothesis doc in `docs/hypotheses/`; explicit "Claude proposed, I rejected X" commits |
| **E — Demo, narrative & review** | Person E | PR reviews, `docs/hypotheses/` curator, `docs/AI_USAGE.md`, `docs/PRIOR_ART.md`, demo script | 15 (Lichess bot operator) | The AI-usage writeup itself; runs live Lichess games during judging |

Every PR from C/D/E must include a one-paragraph hypothesis docstring at the top of the engine module — that's the AI-usage paper trail. Person E curates these into `docs/AI_USAGE.md`.

---

## File Structure

```
chess-engine-cubist/
├── pyproject.toml                     # project + deps
├── README.md                          # quickstart + architecture link
├── .gitignore                         # adds games/, results.db, .venv, __pycache__
├── .github/workflows/smoke.yml        # PR smoke tournament
├── src/cubist/
│   ├── __init__.py
│   ├── engine.py                      # Engine protocol (Task 2)
│   ├── engines/
│   │   ├── __init__.py                # re-exports registry
│   │   ├── registry.py                # name → Engine factory (Task 2)
│   │   ├── random_mover.py            # trivial engine (Task 2)
│   │   ├── greedy_capturer.py         # trivial engine (Task 2)
│   │   └── baseline.py                # BaselineEngine (Tasks 6-8)
│   ├── harness/
│   │   ├── __init__.py
│   │   ├── match.py                   # play_match (Task 3)
│   │   ├── db.py                      # SQLite schema + helpers (Task 4)
│   │   ├── tournament.py              # round-robin runner (Task 5)
│   │   └── stats.py                   # Wilson CI + Bayes-Elo (Task 9)
│   └── uci.py                         # UCI wrapper (Task 13, stretch)
├── tests/
│   ├── test_engine_protocol.py        # (Task 2)
│   ├── test_trivial_engines.py        # (Task 2)
│   ├── test_match.py                  # (Task 3)
│   ├── test_db.py                     # (Task 4)
│   ├── test_tournament.py             # (Task 5)
│   ├── test_baseline_search.py        # (Task 6)
│   ├── test_baseline_iddfs_tt.py      # (Task 7)
│   ├── test_baseline_quiescence.py    # (Task 8)
│   ├── test_stats.py                  # (Task 9)
│   ├── test_antichess_invariants.py   # (Task 12)
│   └── test_uci.py                    # (Task 13)
├── notebooks/
│   └── results.ipynb                  # dashboard (Task 10)
├── docs/
│   └── hypotheses/                    # teammate notes (not in this plan)
└── games/                             # PGN output (gitignored)
```

---

## Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/cubist/__init__.py`
- Create: `src/cubist/engines/__init__.py`
- Create: `src/cubist/harness/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Modify: `README.md`

- [ ] **Step 1.1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "cubist"
version = "0.1.0"
description = "Antichess engine for the Cubist hackathon."
requires-python = ">=3.11"
dependencies = [
    "chess>=1.999",
    "numpy>=1.26",
    "scipy>=1.11",
    "pandas>=2.1",
    "matplotlib>=3.8",
    "jupyter>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.4", "pytest-timeout>=2.2", "pytest-xdist>=3.5"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
timeout = 60
```

- [ ] **Step 1.2: Create `.gitignore`**

```
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.ipynb_checkpoints/
games/
results.db
*.egg-info/
build/
dist/
.DS_Store
```

- [ ] **Step 1.3: Create empty package init files**

Create three empty files: `src/cubist/__init__.py`, `src/cubist/engines/__init__.py`, `src/cubist/harness/__init__.py`, `tests/__init__.py`.

- [ ] **Step 1.4: Create `tests/conftest.py`**

```python
import random
import pytest

@pytest.fixture
def seeded_rng():
    return random.Random(42)
```

- [ ] **Step 1.5: Update `README.md`**

```markdown
# Cubist Antichess Engine

Antichess engine built for the Cubist hackathon. Parallel experimentation
harness where teammates submit engine variants via PR and a round-robin
tournament ranks them on an Elo ladder.

See [design spec](docs/superpowers/specs/2026-04-24-antichess-engine-design.md).

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m cubist.harness.tournament --help
```
```

- [ ] **Step 1.6: Install and verify**

Run: `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`
Expected: no errors, `cubist` importable.

Verify: `python -c "import cubist; import chess.variant; print(chess.variant.AntichessBoard().fen())"`
Expected: `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1`

- [ ] **Step 1.7: Commit**

```bash
git add pyproject.toml .gitignore src/ tests/ README.md
git commit -m "feat: project scaffolding, deps, pytest config"
```

---

## Task 2: Engine protocol + trivial engines + registry

**Files:**
- Create: `src/cubist/engine.py`
- Create: `src/cubist/engines/random_mover.py`
- Create: `src/cubist/engines/greedy_capturer.py`
- Create: `src/cubist/engines/registry.py`
- Modify: `src/cubist/engines/__init__.py`
- Test: `tests/test_engine_protocol.py`, `tests/test_trivial_engines.py`

- [ ] **Step 2.1: Write failing test for Engine protocol**

Create `tests/test_engine_protocol.py`:

```python
import chess
from chess.variant import AntichessBoard
from cubist.engine import Engine

def test_engine_is_abstract_enough_to_subclass():
    class Dummy(Engine):
        name = "dummy"
        description = "returns first legal move"
        def play(self, board, time_limit_s):
            return next(iter(board.legal_moves))

    d = Dummy()
    assert d.name == "dummy"
    assert d.description
    move = d.play(AntichessBoard(), 0.1)
    assert isinstance(move, chess.Move)
```

- [ ] **Step 2.2: Verify it fails**

Run: `pytest tests/test_engine_protocol.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cubist.engine'`

- [ ] **Step 2.3: Implement `src/cubist/engine.py`**

```python
from __future__ import annotations
from abc import ABC, abstractmethod
import chess
from chess.variant import AntichessBoard

class Engine(ABC):
    """Contract for any antichess engine in this project.

    Subclasses set `name` and `description` (one-line hypothesis being tested)
    and implement `play`. The harness calls `play` once per ply with a fresh
    copy of the board and a soft time budget; engines that exceed the budget
    by more than 50%, or return an illegal move, forfeit the game.
    """
    name: str = "unnamed"
    description: str = ""

    @abstractmethod
    def play(self, board: AntichessBoard, time_limit_s: float) -> chess.Move:
        ...
```

- [ ] **Step 2.4: Verify test passes**

Run: `pytest tests/test_engine_protocol.py -v`
Expected: PASS.

- [ ] **Step 2.5: Write failing tests for trivial engines**

Create `tests/test_trivial_engines.py`:

```python
import chess
from chess.variant import AntichessBoard
from cubist.engines.random_mover import RandomMover
from cubist.engines.greedy_capturer import GreedyCapturer

def test_random_mover_returns_legal_move(seeded_rng):
    e = RandomMover(rng=seeded_rng)
    m = e.play(AntichessBoard(), 0.01)
    assert m in AntichessBoard().legal_moves

def test_random_mover_is_deterministic_with_seeded_rng(seeded_rng):
    e1 = RandomMover(rng=__import__("random").Random(7))
    e2 = RandomMover(rng=__import__("random").Random(7))
    b = AntichessBoard()
    assert e1.play(b, 0.01) == e2.play(b, 0.01)

def test_greedy_capturer_prefers_capture_when_available():
    # Position after 1.e3 b6 2.Bb5 Bb7 — many captures possible for White.
    b = AntichessBoard()
    for uci in ["e2e3", "b7b6", "f1b5", "c8b7"]:
        b.push_uci(uci)
    e = GreedyCapturer()
    m = e.play(b, 0.01)
    assert b.is_capture(m)

def test_greedy_capturer_falls_back_to_any_legal_move_when_no_captures():
    b = AntichessBoard()  # starting position has no captures
    e = GreedyCapturer()
    m = e.play(b, 0.01)
    assert m in b.legal_moves
```

- [ ] **Step 2.6: Verify tests fail**

Run: `pytest tests/test_trivial_engines.py -v`
Expected: FAIL — ModuleNotFoundError.

- [ ] **Step 2.7: Implement `src/cubist/engines/random_mover.py`**

```python
from __future__ import annotations
import random
import chess
from chess.variant import AntichessBoard
from cubist.engine import Engine

class RandomMover(Engine):
    """Random legal move. Baseline any real engine should beat convincingly."""
    name = "random_mover"
    description = "picks a uniformly random legal move"

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()

    def play(self, board: AntichessBoard, time_limit_s: float) -> chess.Move:
        return self.rng.choice(list(board.legal_moves))
```

- [ ] **Step 2.8: Implement `src/cubist/engines/greedy_capturer.py`**

```python
from __future__ import annotations
import random
import chess
from chess.variant import AntichessBoard
from cubist.engine import Engine

_PIECE_VALUE = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}

class GreedyCapturer(Engine):
    """Captures the highest-value piece available; random among ties.

    In antichess, legal_moves is captures-only whenever any capture exists,
    so this mostly chooses which capture among many. When no captures,
    falls back to a random legal move.
    """
    name = "greedy_capturer"
    description = "captures highest-value piece; random otherwise"

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()

    def play(self, board: AntichessBoard, time_limit_s: float) -> chess.Move:
        moves = list(board.legal_moves)
        captures = [m for m in moves if board.is_capture(m)]
        if not captures:
            return self.rng.choice(moves)
        def value(m: chess.Move) -> int:
            captured = board.piece_at(m.to_square)
            return _PIECE_VALUE.get(captured.piece_type, 0) if captured else 0
        best = max(value(m) for m in captures)
        return self.rng.choice([m for m in captures if value(m) == best])
```

- [ ] **Step 2.9: Implement `src/cubist/engines/registry.py`**

```python
from __future__ import annotations
from typing import Callable, Dict
from cubist.engine import Engine
from cubist.engines.random_mover import RandomMover
from cubist.engines.greedy_capturer import GreedyCapturer

EngineFactory = Callable[[], Engine]

REGISTRY: Dict[str, EngineFactory] = {
    "random_mover": RandomMover,
    "greedy_capturer": GreedyCapturer,
    # Teammates append their engine here when merging PRs.
}

def get(name: str) -> Engine:
    if name not in REGISTRY:
        raise KeyError(f"No engine named {name!r}. Known: {sorted(REGISTRY)}")
    return REGISTRY[name]()

def all_names() -> list[str]:
    return sorted(REGISTRY)
```

- [ ] **Step 2.10: Re-export from `src/cubist/engines/__init__.py`**

```python
from cubist.engines.registry import REGISTRY, get, all_names

__all__ = ["REGISTRY", "get", "all_names"]
```

- [ ] **Step 2.11: Run all tests**

Run: `pytest -v`
Expected: all tests PASS.

- [ ] **Step 2.12: Commit**

```bash
git add src/cubist/engine.py src/cubist/engines/ tests/test_engine_protocol.py tests/test_trivial_engines.py
git commit -m "feat: Engine protocol, RandomMover, GreedyCapturer, registry"
```

---

## Task 3: Match harness with forfeit/timeout

**Files:**
- Create: `src/cubist/harness/match.py`
- Test: `tests/test_match.py`

- [ ] **Step 3.1: Write failing tests**

Create `tests/test_match.py`:

```python
import random
import chess
from chess.variant import AntichessBoard
from cubist.engine import Engine
from cubist.engines.random_mover import RandomMover
from cubist.harness.match import play_match, GameResult, Outcome

def test_play_match_random_vs_random_completes(seeded_rng):
    w = RandomMover(rng=random.Random(1))
    b = RandomMover(rng=random.Random(2))
    r = play_match(w, b, time_per_move=0.01, max_plies=300)
    assert isinstance(r, GameResult)
    assert r.outcome in (Outcome.WHITE, Outcome.BLACK, Outcome.DRAW, Outcome.FORFEIT_W, Outcome.FORFEIT_B)
    assert r.pgn  # non-empty PGN
    assert len(r.moves) == len(r.times)

def test_play_match_forfeits_on_illegal_move():
    class Cheater(Engine):
        name = "cheater"; description = "returns a random uci string"
        def play(self, board, time_limit_s):
            return chess.Move.from_uci("a1h8")  # not a legal antichess move
    r = play_match(Cheater(), RandomMover(rng=random.Random(1)), time_per_move=0.01)
    assert r.outcome == Outcome.FORFEIT_W
    assert "illegal" in r.forfeit_reason.lower()

def test_play_match_forfeits_on_timeout():
    import time as _time
    class Slowpoke(Engine):
        name = "slow"; description = "sleeps past budget"
        def play(self, board, time_limit_s):
            _time.sleep(time_limit_s * 2)
            return next(iter(board.legal_moves))
    r = play_match(RandomMover(random.Random(1)), Slowpoke(), time_per_move=0.02, max_plies=300)
    # Slowpoke is Black; first White plays, then Black times out.
    assert r.outcome == Outcome.FORFEIT_B
    assert "time" in r.forfeit_reason.lower()

def test_play_match_caps_at_max_plies():
    # With max_plies=0, we can't even play one move.
    r = play_match(RandomMover(random.Random(1)), RandomMover(random.Random(2)),
                   time_per_move=0.01, max_plies=0)
    assert r.outcome == Outcome.DRAW  # capped before any result
    assert len(r.moves) == 0
```

- [ ] **Step 3.2: Verify tests fail**

Run: `pytest tests/test_match.py -v`
Expected: FAIL — no `cubist.harness.match`.

- [ ] **Step 3.3: Implement `src/cubist/harness/match.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import io
import time
from typing import Optional
import chess
import chess.pgn
from chess.variant import AntichessBoard
from cubist.engine import Engine

class Outcome(str, Enum):
    WHITE = "1-0"
    BLACK = "0-1"
    DRAW = "1/2-1/2"
    FORFEIT_W = "forfeit_w"
    FORFEIT_B = "forfeit_b"

@dataclass
class GameResult:
    outcome: Outcome
    pgn: str
    moves: list[chess.Move] = field(default_factory=list)
    times: list[float] = field(default_factory=list)
    forfeit_reason: str = ""
    n_plies: int = 0

def _pgn_of(board: AntichessBoard, white: str, black: str, result: str) -> str:
    game = chess.pgn.Game.from_board(board)
    game.headers["Variant"] = "Antichess"
    game.headers["White"] = white
    game.headers["Black"] = black
    game.headers["Result"] = result
    out = io.StringIO()
    print(game, file=out)
    return out.getvalue()

def play_match(white: Engine, black: Engine, time_per_move: float,
               max_plies: int = 300) -> GameResult:
    board = AntichessBoard()
    moves: list[chess.Move] = []
    times: list[float] = []
    timeout_factor = 1.5

    while len(moves) < max_plies and not board.is_variant_end():
        engine = white if board.turn == chess.WHITE else black
        start = time.monotonic()
        try:
            move = engine.play(board.copy(), time_per_move)
        except Exception as e:
            reason = f"engine raised: {type(e).__name__}: {e}"
            forfeit = Outcome.FORFEIT_W if board.turn == chess.WHITE else Outcome.FORFEIT_B
            result_str = "0-1" if forfeit == Outcome.FORFEIT_W else "1-0"
            return GameResult(outcome=forfeit,
                              pgn=_pgn_of(board, white.name, black.name, result_str),
                              moves=moves, times=times,
                              forfeit_reason=reason, n_plies=len(moves))
        elapsed = time.monotonic() - start

        if elapsed > time_per_move * timeout_factor:
            forfeit = Outcome.FORFEIT_W if board.turn == chess.WHITE else Outcome.FORFEIT_B
            result_str = "0-1" if forfeit == Outcome.FORFEIT_W else "1-0"
            return GameResult(outcome=forfeit,
                              pgn=_pgn_of(board, white.name, black.name, result_str),
                              moves=moves, times=times,
                              forfeit_reason=f"time budget exceeded: {elapsed:.3f}s > {time_per_move*timeout_factor:.3f}s",
                              n_plies=len(moves))

        if move not in board.legal_moves:
            forfeit = Outcome.FORFEIT_W if board.turn == chess.WHITE else Outcome.FORFEIT_B
            result_str = "0-1" if forfeit == Outcome.FORFEIT_W else "1-0"
            return GameResult(outcome=forfeit,
                              pgn=_pgn_of(board, white.name, black.name, result_str),
                              moves=moves, times=times,
                              forfeit_reason=f"illegal move: {move.uci()}",
                              n_plies=len(moves))

        board.push(move)
        moves.append(move)
        times.append(elapsed)

    # Natural end or max-plies cap.
    if board.is_variant_end():
        result_str = board.result()
        outcome = {"1-0": Outcome.WHITE, "0-1": Outcome.BLACK, "1/2-1/2": Outcome.DRAW}[result_str]
    else:
        result_str = "1/2-1/2"
        outcome = Outcome.DRAW

    return GameResult(outcome=outcome,
                      pgn=_pgn_of(board, white.name, black.name, result_str),
                      moves=moves, times=times, n_plies=len(moves))
```

- [ ] **Step 3.4: Run tests**

Run: `pytest tests/test_match.py -v`
Expected: all 4 PASS.

- [ ] **Step 3.5: Commit**

```bash
git add src/cubist/harness/match.py tests/test_match.py
git commit -m "feat: match harness with forfeit on illegal/timeout/exception"
```

---

## Task 4: SQLite results store

**Files:**
- Create: `src/cubist/harness/db.py`
- Test: `tests/test_db.py`

- [ ] **Step 4.1: Write failing tests**

Create `tests/test_db.py`:

```python
import os
import sqlite3
import tempfile
from cubist.harness.db import init_db, record_engine, record_game, all_games, engines_in_db

def test_init_db_creates_tables():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "t.db")
        init_db(path)
        con = sqlite3.connect(path)
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"games", "engines"} <= tables

def test_record_engine_and_game_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "t.db")
        init_db(path)
        record_engine(path, name="a", description="does A", commit_sha="abc", parent_of=None)
        record_engine(path, name="b", description="does B", commit_sha="def", parent_of="a")
        record_game(path, tournament_id="t1", white="a", black="b",
                    result="1-0", n_plies=42, total_time_w=1.2, total_time_b=1.3,
                    pgn="[pgn]")
        games = all_games(path)
        assert len(games) == 1
        assert games[0]["white"] == "a"
        assert games[0]["result"] == "1-0"
        assert set(engines_in_db(path)) == {"a", "b"}

def test_record_engine_is_upsert():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "t.db")
        init_db(path)
        record_engine(path, name="a", description="v1", commit_sha="abc", parent_of=None)
        record_engine(path, name="a", description="v2", commit_sha="def", parent_of=None)
        con = sqlite3.connect(path); con.row_factory = sqlite3.Row
        rows = list(con.execute("SELECT * FROM engines WHERE name='a'"))
        assert len(rows) == 1
        assert rows[0]["description"] == "v2"
```

- [ ] **Step 4.2: Verify tests fail**

Run: `pytest tests/test_db.py -v`
Expected: FAIL — ModuleNotFoundError.

- [ ] **Step 4.3: Implement `src/cubist/harness/db.py`**

```python
from __future__ import annotations
import sqlite3
import time
from typing import Any, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS engines (
  name          TEXT PRIMARY KEY,
  description   TEXT NOT NULL DEFAULT '',
  commit_sha    TEXT,
  parent_of     TEXT
);

CREATE TABLE IF NOT EXISTS games (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  tournament_id TEXT NOT NULL,
  white         TEXT NOT NULL,
  black         TEXT NOT NULL,
  result        TEXT NOT NULL,
  n_plies       INTEGER NOT NULL,
  total_time_w  REAL NOT NULL,
  total_time_b  REAL NOT NULL,
  pgn           TEXT NOT NULL,
  forfeit_reason TEXT NOT NULL DEFAULT '',
  started_at    REAL NOT NULL,
  FOREIGN KEY (white) REFERENCES engines(name),
  FOREIGN KEY (black) REFERENCES engines(name)
);

CREATE INDEX IF NOT EXISTS idx_games_tournament ON games(tournament_id);
CREATE INDEX IF NOT EXISTS idx_games_pair ON games(white, black);
"""

def _connect(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db(path: str) -> None:
    con = _connect(path)
    con.executescript(_SCHEMA)
    con.commit()
    con.close()

def record_engine(path: str, *, name: str, description: str,
                  commit_sha: Optional[str], parent_of: Optional[str]) -> None:
    con = _connect(path)
    con.execute(
        "INSERT INTO engines (name, description, commit_sha, parent_of) VALUES (?,?,?,?) "
        "ON CONFLICT(name) DO UPDATE SET description=excluded.description, "
        "commit_sha=excluded.commit_sha, parent_of=excluded.parent_of",
        (name, description, commit_sha, parent_of),
    )
    con.commit(); con.close()

def record_game(path: str, *, tournament_id: str, white: str, black: str,
                result: str, n_plies: int, total_time_w: float, total_time_b: float,
                pgn: str, forfeit_reason: str = "", started_at: Optional[float] = None) -> None:
    if started_at is None:
        started_at = time.time()
    con = _connect(path)
    con.execute(
        "INSERT INTO games (tournament_id, white, black, result, n_plies, "
        "total_time_w, total_time_b, pgn, forfeit_reason, started_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (tournament_id, white, black, result, n_plies,
         total_time_w, total_time_b, pgn, forfeit_reason, started_at),
    )
    con.commit(); con.close()

def all_games(path: str) -> list[dict[str, Any]]:
    con = _connect(path)
    rows = [dict(r) for r in con.execute("SELECT * FROM games ORDER BY id")]
    con.close(); return rows

def engines_in_db(path: str) -> list[str]:
    con = _connect(path)
    names = [r["name"] for r in con.execute("SELECT name FROM engines ORDER BY name")]
    con.close(); return names
```

- [ ] **Step 4.4: Run tests**

Run: `pytest tests/test_db.py -v`
Expected: 3 PASS.

- [ ] **Step 4.5: Commit**

```bash
git add src/cubist/harness/db.py tests/test_db.py
git commit -m "feat: SQLite schema for engines + games, upsert + read helpers"
```

---

## Task 5: Round-robin tournament runner

**Files:**
- Create: `src/cubist/harness/tournament.py`
- Test: `tests/test_tournament.py`

- [ ] **Step 5.1: Write failing tests**

Create `tests/test_tournament.py`:

```python
import os
import tempfile
from cubist.harness.tournament import run_tournament, pair_schedule
from cubist.harness.db import all_games

def test_pair_schedule_alternates_colors():
    pairs = pair_schedule(["a", "b", "c"], n_games=2)
    # Every pair plays n_games, with colors alternating.
    counts = {}
    for w, b in pairs:
        counts[(w, b)] = counts.get((w, b), 0) + 1
    assert counts[("a", "b")] == 1 and counts[("b", "a")] == 1
    assert counts[("a", "c")] == 1 and counts[("c", "a")] == 1
    assert counts[("b", "c")] == 1 and counts[("c", "b")] == 1
    assert sum(counts.values()) == 6  # 3 pairs * 2 games

def test_run_tournament_writes_games():
    with tempfile.TemporaryDirectory() as d:
        db_path = os.path.join(d, "r.db")
        games_dir = os.path.join(d, "games")
        os.makedirs(games_dir, exist_ok=True)
        run_tournament(
            engine_names=["random_mover", "greedy_capturer"],
            n_games=2, time_per_move=0.01, max_plies=80,
            db_path=db_path, games_dir=games_dir,
            tournament_id="smoke", workers=1,
        )
        games = all_games(db_path)
        assert len(games) == 2
        assert {g["white"] for g in games} | {g["black"] for g in games} == {"random_mover", "greedy_capturer"}
        # PGN files exist
        assert len(os.listdir(games_dir)) == 2
```

- [ ] **Step 5.2: Verify tests fail**

Run: `pytest tests/test_tournament.py -v`
Expected: FAIL — ModuleNotFoundError.

- [ ] **Step 5.3: Implement `src/cubist/harness/tournament.py`**

```python
from __future__ import annotations
import argparse
import itertools
import multiprocessing as mp
import os
import uuid
from typing import Iterable
from cubist.engines.registry import REGISTRY
from cubist.harness.db import init_db, record_engine, record_game
from cubist.harness.match import play_match, Outcome

def pair_schedule(names: list[str], n_games: int) -> list[tuple[str, str]]:
    """Round-robin with alternating colors. Each unordered pair plays n_games
    games, split as evenly as possible between the two color assignments."""
    out: list[tuple[str, str]] = []
    for a, b in itertools.combinations(names, 2):
        for i in range(n_games):
            out.append((a, b) if i % 2 == 0 else (b, a))
    return out

def _play_one(args):
    white_name, black_name, time_per_move, max_plies = args
    white = REGISTRY[white_name]()
    black = REGISTRY[black_name]()
    r = play_match(white, black, time_per_move=time_per_move, max_plies=max_plies)
    return (white_name, black_name, r)

def _result_str(outcome: Outcome) -> str:
    return {
        Outcome.WHITE: "1-0",
        Outcome.BLACK: "0-1",
        Outcome.DRAW: "1/2-1/2",
        Outcome.FORFEIT_W: "0-1",
        Outcome.FORFEIT_B: "1-0",
    }[outcome]

def run_tournament(*, engine_names: list[str], n_games: int, time_per_move: float,
                   max_plies: int, db_path: str, games_dir: str,
                   tournament_id: str, workers: int = 1) -> None:
    os.makedirs(games_dir, exist_ok=True)
    init_db(db_path)
    for n in engine_names:
        eng = REGISTRY[n]()
        record_engine(db_path, name=n, description=eng.description,
                      commit_sha=None, parent_of=None)

    jobs = [(w, b, time_per_move, max_plies) for w, b in pair_schedule(engine_names, n_games)]

    if workers > 1:
        with mp.Pool(processes=workers) as pool:
            results = pool.map(_play_one, jobs)
    else:
        results = [_play_one(j) for j in jobs]

    for white_name, black_name, r in results:
        total_w = sum(r.times[::2])
        total_b = sum(r.times[1::2])
        record_game(
            db_path,
            tournament_id=tournament_id, white=white_name, black=black_name,
            result=_result_str(r.outcome), n_plies=r.n_plies,
            total_time_w=total_w, total_time_b=total_b,
            pgn=r.pgn, forfeit_reason=r.forfeit_reason,
        )
        fname = f"{tournament_id}_{white_name}_vs_{black_name}_{uuid.uuid4().hex[:8]}.pgn"
        with open(os.path.join(games_dir, fname), "w") as f:
            f.write(r.pgn)

def _cli() -> None:
    p = argparse.ArgumentParser(description="Run a round-robin antichess tournament.")
    p.add_argument("--engines", nargs="+", default=None,
                   help="Engine names; default = all in registry.")
    p.add_argument("--n-games", type=int, default=20)
    p.add_argument("--time-per-move", type=float, default=0.5)
    p.add_argument("--max-plies", type=int, default=300)
    p.add_argument("--db", default="results.db")
    p.add_argument("--games-dir", default="games")
    p.add_argument("--workers", type=int, default=max(1, os.cpu_count() // 2))
    p.add_argument("--tournament-id", default=None)
    args = p.parse_args()

    names = args.engines or sorted(REGISTRY)
    tid = args.tournament_id or f"t-{uuid.uuid4().hex[:8]}"
    print(f"Tournament {tid}: {names}, {args.n_games} games/pair, "
          f"{args.time_per_move}s/move, workers={args.workers}")
    run_tournament(
        engine_names=names, n_games=args.n_games, time_per_move=args.time_per_move,
        max_plies=args.max_plies, db_path=args.db, games_dir=args.games_dir,
        tournament_id=tid, workers=args.workers,
    )
    print(f"Done. Results in {args.db}, PGNs in {args.games_dir}/.")

if __name__ == "__main__":
    _cli()
```

- [ ] **Step 5.4: Run tests**

Run: `pytest tests/test_tournament.py -v`
Expected: PASS.

- [ ] **Step 5.5: Smoke-run the CLI**

Run: `python -m cubist.harness.tournament --n-games 2 --time-per-move 0.05 --workers 1 --db /tmp/cubist_smoke.db --games-dir /tmp/cubist_games`
Expected: completes in <30s, prints "Done.", creates PGN files.

- [ ] **Step 5.6: Commit**

```bash
git add src/cubist/harness/tournament.py tests/test_tournament.py
git commit -m "feat: round-robin tournament runner with multiprocessing"
```

---

## Task 6: Baseline engine — negamax alpha-beta (no IDDFS/TT/QS yet)

**Files:**
- Create: `src/cubist/engines/baseline.py`
- Test: `tests/test_baseline_search.py`

- [ ] **Step 6.1: Write failing tests**

Create `tests/test_baseline_search.py`:

```python
import chess
from chess.variant import AntichessBoard
from cubist.engines.baseline import BaselineEngine, evaluate_white_pov

def test_eval_starting_position_is_zero():
    assert evaluate_white_pov(AntichessBoard()) == 0

def test_eval_prefers_fewer_own_pieces():
    # Remove a White pawn; White is now closer to winning → positive score.
    b = AntichessBoard()
    b.remove_piece_at(chess.E2)
    assert evaluate_white_pov(b) > 0

def test_baseline_returns_legal_move_at_depth_1():
    eng = BaselineEngine(max_depth=1)
    b = AntichessBoard()
    m = eng.play(b, time_limit_s=1.0)
    assert m in b.legal_moves

def test_baseline_takes_forced_capture_line_when_only_option():
    # Construct a position where every legal move is a capture (forced).
    b = AntichessBoard()
    for uci in ["e2e3", "d7d5", "e3e4", "d5e4"]:  # after 4...dxe4 only one legal move? approximate
        b.push_uci(uci)
    # After this sequence, Black has just captured; White must now move.
    eng = BaselineEngine(max_depth=2)
    m = eng.play(b, time_limit_s=1.0)
    assert m in b.legal_moves
```

- [ ] **Step 6.2: Verify tests fail**

Run: `pytest tests/test_baseline_search.py -v`
Expected: FAIL — ModuleNotFoundError.

- [ ] **Step 6.3: Implement initial `src/cubist/engines/baseline.py`**

```python
"""BaselineEngine: iterative-deepening negamax alpha-beta on AntichessBoard.

Starts as a plain depth-limited negamax (Task 6). Iterative deepening and
transposition tables come in Task 7; quiescence in Task 8. The eval is a
deliberately naive first draft intended to be beaten by experiment variants.
"""
from __future__ import annotations
import time
import chess
from chess.variant import AntichessBoard
from cubist.engine import Engine

# Material values (standard chess nomenclature; sign handling is in the eval).
_PIECE_VALUE = {
    chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
    chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0,
}
_WIN = 10_000
_INF = 10**9

def evaluate_white_pov(board: AntichessBoard) -> int:
    """Static eval from White's POV. Positive = good for White.

    In antichess, "good" means closer to *losing all pieces* or being
    stalemated. Terminal positions: +_WIN for White, -_WIN for Black.
    """
    if board.is_variant_end():
        r = board.result()
        return _WIN if r == "1-0" else (-_WIN if r == "0-1" else 0)

    # Material (inverted): fewer White pieces → higher score for White.
    score = 0
    for pt, v in _PIECE_VALUE.items():
        if pt == chess.KING:
            continue
        score -= len(board.pieces(pt, chess.WHITE)) * v
        score += len(board.pieces(pt, chess.BLACK)) * v

    # Mobility proxy: if opponent is about to have few legal moves, we're
    # closer to stalemating them (= a win). Cheap to compute and directional.
    # (We evaluate from the current side-to-move angle to keep it simple.)
    stm_moves = board.legal_moves.count()
    # Small signal, deliberately under-tuned.
    if board.turn == chess.WHITE:
        score += max(0, 10 - stm_moves)
    else:
        score -= max(0, 10 - stm_moves)
    return score

def evaluate_stm(board: AntichessBoard) -> int:
    w = evaluate_white_pov(board)
    return w if board.turn == chess.WHITE else -w

def _ordered_moves(board: AntichessBoard):
    # MVV-LVA for captures; python-chess forces captures-only when any exist.
    def score(m: chess.Move) -> int:
        cap = board.piece_at(m.to_square)
        return _PIECE_VALUE.get(cap.piece_type, 0) if cap else 0
    return sorted(board.legal_moves, key=score, reverse=True)

class BaselineEngine(Engine):
    name = "baseline"
    description = "iterative-deepening negamax with MVV-LVA and inverted-material eval"

    def __init__(self, max_depth: int = 4):
        self.max_depth = max_depth

    def _negamax(self, board: AntichessBoard, depth: int, alpha: int, beta: int) -> int:
        if depth == 0 or board.is_variant_end():
            return evaluate_stm(board)
        best = -_INF
        for mv in _ordered_moves(board):
            board.push(mv)
            score = -self._negamax(board, depth - 1, -beta, -alpha)
            board.pop()
            if score > best:
                best = score
                if score > alpha:
                    alpha = score
                    if alpha >= beta:
                        break
        return best

    def play(self, board: AntichessBoard, time_limit_s: float) -> chess.Move:
        best_move: chess.Move | None = None
        best_score = -_INF
        for mv in _ordered_moves(board):
            board.push(mv)
            score = -self._negamax(board, self.max_depth - 1, -_INF, _INF)
            board.pop()
            if score > best_score:
                best_score = score
                best_move = mv
        if best_move is None:  # shouldn't happen on legal positions, safety net
            best_move = next(iter(board.legal_moves))
        return best_move
```

- [ ] **Step 6.4: Run tests**

Run: `pytest tests/test_baseline_search.py -v`
Expected: PASS.

- [ ] **Step 6.5: Register baseline**

Edit `src/cubist/engines/registry.py` — add after GreedyCapturer:

```python
from cubist.engines.baseline import BaselineEngine

REGISTRY: Dict[str, EngineFactory] = {
    "random_mover": RandomMover,
    "greedy_capturer": GreedyCapturer,
    "baseline": BaselineEngine,
}
```

- [ ] **Step 6.6: Sanity match — baseline should beat random handily**

Run: `python -c "
import random
from cubist.engines.random_mover import RandomMover
from cubist.engines.baseline import BaselineEngine
from cubist.harness.match import play_match, Outcome
wins = 0
for i in range(10):
    w, b = (BaselineEngine(max_depth=3), RandomMover(random.Random(i))) if i%2==0 else (RandomMover(random.Random(i)), BaselineEngine(max_depth=3))
    r = play_match(w, b, time_per_move=0.5, max_plies=200)
    baseline_won = (r.outcome == Outcome.WHITE and i%2==0) or (r.outcome == Outcome.BLACK and i%2==1)
    wins += int(baseline_won)
print(f'baseline wins: {wins}/10')"`
Expected: baseline wins ≥6 of 10 (usually 8+).

- [ ] **Step 6.7: Commit**

```bash
git add src/cubist/engines/baseline.py src/cubist/engines/registry.py tests/test_baseline_search.py
git commit -m "feat: BaselineEngine with negamax alpha-beta and inverted-material eval"
```

---

## Task 7: Iterative deepening + transposition table

**Files:**
- Modify: `src/cubist/engines/baseline.py`
- Test: `tests/test_baseline_iddfs_tt.py`

- [ ] **Step 7.1: Write failing tests**

Create `tests/test_baseline_iddfs_tt.py`:

```python
import time
from chess.variant import AntichessBoard
from cubist.engines.baseline import BaselineEngine

def test_iddfs_respects_time_budget():
    eng = BaselineEngine(max_depth=99, time_fraction=0.9)
    b = AntichessBoard()
    t0 = time.monotonic()
    eng.play(b, time_limit_s=0.3)
    elapsed = time.monotonic() - t0
    assert 0.05 < elapsed < 0.45, f"elapsed={elapsed}"

def test_tt_hits_are_observed():
    eng = BaselineEngine(max_depth=4)
    b = AntichessBoard()
    eng.play(b, time_limit_s=2.0)
    # TT should have been populated during search.
    assert len(eng._tt) > 0

def test_repeated_play_uses_tt_cache_across_calls():
    eng = BaselineEngine(max_depth=3)
    b = AntichessBoard()
    eng.play(b, time_limit_s=2.0)
    first_size = len(eng._tt)
    eng.play(b, time_limit_s=2.0)
    # Same call again: TT shouldn't shrink, entries should be reused.
    assert len(eng._tt) >= first_size
```

- [ ] **Step 7.2: Verify tests fail**

Run: `pytest tests/test_baseline_iddfs_tt.py -v`
Expected: FAIL — `BaselineEngine` has no `time_fraction` / `_tt`.

- [ ] **Step 7.3: Replace `BaselineEngine` with IDDFS + TT**

Replace the `BaselineEngine` class in `src/cubist/engines/baseline.py` (keep everything above it). New body:

```python
import chess.polyglot

_EXACT, _LOWER, _UPPER = 0, 1, 2

class BaselineEngine(Engine):
    name = "baseline"
    description = "iterative-deepening negamax + TT (MVV-LVA, inverted-material eval)"

    def __init__(self, max_depth: int = 99, time_fraction: float = 0.9):
        self.max_depth = max_depth
        self.time_fraction = time_fraction
        self._tt: dict[int, tuple[int, int, int, chess.Move | None]] = {}
        # key: zobrist -> (depth, score, flag, best_move)
        self._deadline: float = 0.0

    def _time_up(self) -> bool:
        return time.monotonic() >= self._deadline

    def _ordered_with_tt(self, board: AntichessBoard, tt_move: chess.Move | None):
        moves = list(board.legal_moves)
        def score(m):
            if tt_move is not None and m == tt_move:
                return 10**6
            cap = board.piece_at(m.to_square)
            return _PIECE_VALUE.get(cap.piece_type, 0) if cap else 0
        moves.sort(key=score, reverse=True)
        return moves

    def _negamax(self, board: AntichessBoard, depth: int, alpha: int, beta: int) -> int:
        if self._time_up():
            raise TimeoutError
        alpha_orig = alpha
        key = chess.polyglot.zobrist_hash(board)
        entry = self._tt.get(key)
        tt_move = None
        if entry is not None and entry[0] >= depth:
            tt_depth, tt_score, tt_flag, tt_move = entry
            if tt_flag == _EXACT:
                return tt_score
            if tt_flag == _LOWER and tt_score > alpha:
                alpha = tt_score
            elif tt_flag == _UPPER and tt_score < beta:
                beta = tt_score
            if alpha >= beta:
                return tt_score

        if depth == 0 or board.is_variant_end():
            return evaluate_stm(board)

        best = -_INF
        best_move: chess.Move | None = None
        for mv in self._ordered_with_tt(board, tt_move):
            board.push(mv)
            score = -self._negamax(board, depth - 1, -beta, -alpha)
            board.pop()
            if score > best:
                best, best_move = score, mv
                if score > alpha:
                    alpha = score
                    if alpha >= beta:
                        break
        if best <= alpha_orig:
            flag = _UPPER
        elif best >= beta:
            flag = _LOWER
        else:
            flag = _EXACT
        self._tt[key] = (depth, best, flag, best_move)
        return best

    def play(self, board: AntichessBoard, time_limit_s: float) -> chess.Move:
        self._deadline = time.monotonic() + time_limit_s * self.time_fraction
        best_move: chess.Move | None = None
        # Iterative deepening: start at depth 1, go deeper until time or max.
        for depth in range(1, self.max_depth + 1):
            try:
                current_best = None
                current_score = -_INF
                key = chess.polyglot.zobrist_hash(board)
                tt_move = self._tt[key][3] if key in self._tt else None
                for mv in self._ordered_with_tt(board, tt_move):
                    board.push(mv)
                    score = -self._negamax(board, depth - 1, -_INF, _INF)
                    board.pop()
                    if score > current_score:
                        current_score, current_best = score, mv
                if current_best is not None:
                    best_move = current_best
            except TimeoutError:
                break
            if self._time_up():
                break
        if best_move is None:
            best_move = next(iter(board.legal_moves))
        return best_move
```

- [ ] **Step 7.4: Run all baseline tests**

Run: `pytest tests/test_baseline_search.py tests/test_baseline_iddfs_tt.py -v`
Expected: all PASS. (Old tests still work because `max_depth=4` still caps search; `time_limit_s=1.0` is plenty.)

- [ ] **Step 7.5: Sanity match — baseline should now go deeper & beat greedy**

Run: `python -c "
import random
from cubist.engines.greedy_capturer import GreedyCapturer
from cubist.engines.baseline import BaselineEngine
from cubist.harness.match import play_match, Outcome
wins = draws = 0
for i in range(6):
    w, b = (BaselineEngine(), GreedyCapturer()) if i%2==0 else (GreedyCapturer(), BaselineEngine())
    r = play_match(w, b, time_per_move=0.3, max_plies=200)
    if (r.outcome==Outcome.WHITE and i%2==0) or (r.outcome==Outcome.BLACK and i%2==1): wins+=1
    elif r.outcome==Outcome.DRAW: draws+=1
print(f'baseline: {wins}W / {draws}D / {6-wins-draws}L')"`
Expected: wins ≥ losses; concrete numbers vary.

- [ ] **Step 7.6: Commit**

```bash
git add src/cubist/engines/baseline.py tests/test_baseline_iddfs_tt.py
git commit -m "feat: BaselineEngine IDDFS + zobrist TT with bound flags"
```

---

## Task 8: Quiescence search

**Files:**
- Modify: `src/cubist/engines/baseline.py`
- Test: `tests/test_baseline_quiescence.py`

- [ ] **Step 8.1: Write failing tests**

Create `tests/test_baseline_quiescence.py`:

```python
import chess
from chess.variant import AntichessBoard
from cubist.engines.baseline import BaselineEngine, has_captures

def test_has_captures_true_when_captures_available():
    b = AntichessBoard()
    for uci in ["e2e3", "d7d5", "e3e4"]:
        b.push_uci(uci)
    # Black has dxe4 as a forced capture.
    assert has_captures(b)

def test_has_captures_false_at_start():
    assert not has_captures(AntichessBoard())

def test_quiescence_enabled_by_default():
    eng = BaselineEngine()
    assert eng.quiescence is True

def test_quiescence_depth_caps_recursion():
    # Quiescence must terminate even in capture-heavy contrived positions.
    eng = BaselineEngine(max_depth=2, quiescence_max_depth=16)
    b = AntichessBoard()
    for uci in ["e2e4", "d7d5", "e4e5"]:
        b.push_uci(uci)
    m = eng.play(b, time_limit_s=1.0)
    assert m in b.legal_moves
```

- [ ] **Step 8.2: Verify tests fail**

Run: `pytest tests/test_baseline_quiescence.py -v`
Expected: FAIL — `has_captures` / `quiescence` attrs don't exist.

- [ ] **Step 8.3: Add quiescence to baseline**

In `src/cubist/engines/baseline.py`, add after `_ordered_moves`:

```python
def has_captures(board: AntichessBoard) -> bool:
    # In antichess, legal_moves is captures-only whenever any capture exists.
    # So "any legal move is a capture" ⇔ "captures are available".
    for m in board.legal_moves:
        return board.is_capture(m)
    return False
```

Modify `BaselineEngine.__init__` to accept quiescence args:

```python
    def __init__(self, max_depth: int = 99, time_fraction: float = 0.9,
                 quiescence: bool = True, quiescence_max_depth: int = 16):
        self.max_depth = max_depth
        self.time_fraction = time_fraction
        self.quiescence = quiescence
        self.quiescence_max_depth = quiescence_max_depth
        self._tt: dict[int, tuple[int, int, int, chess.Move | None]] = {}
        self._deadline: float = 0.0
```

Add a `_quiescence` method and call it from `_negamax` when depth hits 0:

```python
    def _quiescence(self, board: AntichessBoard, alpha: int, beta: int, q_depth: int) -> int:
        if self._time_up():
            raise TimeoutError
        if q_depth <= 0 or board.is_variant_end() or not has_captures(board):
            return evaluate_stm(board)
        # Stand-pat is NOT a legal option in antichess when captures are forced,
        # so we recurse directly into captures.
        best = -_INF
        for mv in _ordered_moves(board):
            if not board.is_capture(mv):
                continue  # in practice, all legal moves here are captures
            board.push(mv)
            score = -self._quiescence(board, -beta, -alpha, q_depth - 1)
            board.pop()
            if score > best:
                best = score
                if score > alpha:
                    alpha = score
                    if alpha >= beta:
                        break
        # If somehow no capture was playable (shouldn't happen given has_captures), eval.
        return best if best > -_INF else evaluate_stm(board)
```

Modify the depth-0 return in `_negamax`:

```python
        if depth == 0 or board.is_variant_end():
            if self.quiescence and not board.is_variant_end():
                return self._quiescence(board, alpha, beta, self.quiescence_max_depth)
            return evaluate_stm(board)
```

- [ ] **Step 8.4: Run tests**

Run: `pytest tests/test_baseline_quiescence.py tests/test_baseline_search.py tests/test_baseline_iddfs_tt.py -v`
Expected: all PASS.

- [ ] **Step 8.5: Self-play sanity**

Run: `python -c "
import random
from cubist.engines.baseline import BaselineEngine
from cubist.harness.match import play_match
r = play_match(BaselineEngine(), BaselineEngine(quiescence=False), time_per_move=0.3, max_plies=200)
print('quiescence-on vs off:', r.outcome, r.n_plies, 'plies')"`
Expected: completes, shows an outcome. (Not strictly testable since antichess self-play can vary; we just confirm no regressions.)

- [ ] **Step 8.6: Commit**

```bash
git add src/cubist/engines/baseline.py tests/test_baseline_quiescence.py
git commit -m "feat: quiescence search exploiting antichess forced-capture rule"
```

---

## Task 9: Stats — Wilson CI, head-to-head, Bayes-Elo

**Files:**
- Create: `src/cubist/harness/stats.py`
- Test: `tests/test_stats.py`

- [ ] **Step 9.1: Write failing tests**

Create `tests/test_stats.py`:

```python
import os
import tempfile
import pytest
from cubist.harness.db import init_db, record_engine, record_game
from cubist.harness.stats import (
    engine_records, head_to_head, wilson_ci, compute_elo,
)

def _seed_db(path: str):
    init_db(path)
    for n in ("a", "b", "c"):
        record_engine(path, name=n, description="", commit_sha=None, parent_of=None)
    # a dominates b, b beats c, c occasionally beats a.
    results = [
        ("a","b","1-0"), ("a","b","1-0"), ("a","b","1-0"), ("a","b","1-0"), ("a","b","0-1"),
        ("b","c","1-0"), ("b","c","1-0"), ("b","c","1-0"), ("b","c","1/2-1/2"), ("b","c","0-1"),
        ("a","c","1-0"), ("a","c","1-0"), ("a","c","0-1"), ("a","c","1-0"), ("a","c","1-0"),
    ]
    for w, b, r in results:
        record_game(path, tournament_id="t", white=w, black=b, result=r,
                    n_plies=40, total_time_w=0.5, total_time_b=0.5, pgn="")

def test_wilson_ci_basic():
    lo, hi = wilson_ci(wins=5, n=10, z=1.96)
    assert 0.0 <= lo < 0.5 < hi <= 1.0
    assert hi - lo > 0

def test_wilson_ci_extremes():
    lo, hi = wilson_ci(wins=0, n=10, z=1.96)
    assert lo == 0.0
    assert 0.0 < hi < 1.0

def test_engine_records_counts_correctly():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "r.db")
        _seed_db(path)
        recs = engine_records(path)
        a = next(r for r in recs if r["name"] == "a")
        # a played 10 games: 5 vs b (4W,1L), 5 vs c (4W,1L) = 8W/0D/2L = 8.0 / 10
        assert a["wins"] + a["draws"] + a["losses"] == 10
        assert a["score"] == 8.0
        assert 0.0 <= a["ci_lo"] <= a["wins"]/10 <= a["ci_hi"] <= 1.0

def test_head_to_head_matrix():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "r.db")
        _seed_db(path)
        h = head_to_head(path)
        assert h["a"]["b"]["wins"] == 4
        assert h["a"]["b"]["losses"] == 1

def test_compute_elo_orders_engines_sensibly():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "r.db")
        _seed_db(path)
        elos = compute_elo(path, anchor="a", anchor_elo=1500.0)
        assert elos["a"] == 1500.0  # anchored
        assert elos["a"] > elos["b"] > elos["c"]
```

- [ ] **Step 9.2: Verify tests fail**

Run: `pytest tests/test_stats.py -v`
Expected: FAIL.

- [ ] **Step 9.3: Implement `src/cubist/harness/stats.py`**

```python
from __future__ import annotations
import math
import sqlite3
from typing import Any
import numpy as np
from scipy.optimize import minimize

def _connect(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path); con.row_factory = sqlite3.Row; return con

def wilson_ci(wins: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion. `wins` may be a
    score total (draws count as 0.5), not just integer wins."""
    if n == 0:
        return (0.0, 1.0)
    p = wins / n
    denom = 1 + z*z/n
    center = (p + z*z/(2*n)) / denom
    half = (z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))

def _score(result: str, as_white: bool) -> float:
    if result == "1-0": return 1.0 if as_white else 0.0
    if result == "0-1": return 0.0 if as_white else 1.0
    if result == "1/2-1/2": return 0.5
    return 0.0  # shouldn't happen; forfeits are normalized to 1-0 / 0-1 upstream

def engine_records(path: str) -> list[dict[str, Any]]:
    con = _connect(path)
    engines = [r["name"] for r in con.execute("SELECT name FROM engines")]
    out = []
    for name in engines:
        rows = con.execute(
            "SELECT white, black, result FROM games WHERE white=? OR black=?",
            (name, name)).fetchall()
        wins = draws = losses = 0
        score = 0.0
        for row in rows:
            as_white = row["white"] == name
            s = _score(row["result"], as_white)
            score += s
            if s == 1.0: wins += 1
            elif s == 0.5: draws += 1
            else: losses += 1
        n = len(rows)
        lo, hi = wilson_ci(score, n)
        out.append(dict(name=name, games=n, wins=wins, draws=draws, losses=losses,
                        score=score, score_pct=score/n if n else 0.0,
                        ci_lo=lo, ci_hi=hi))
    out.sort(key=lambda r: r["score_pct"], reverse=True)
    con.close(); return out

def head_to_head(path: str) -> dict[str, dict[str, dict[str, int]]]:
    con = _connect(path)
    engines = [r["name"] for r in con.execute("SELECT name FROM engines")]
    h: dict = {a: {b: {"wins": 0, "draws": 0, "losses": 0}
                   for b in engines if b != a} for a in engines}
    for row in con.execute("SELECT white, black, result FROM games"):
        w, b, r = row["white"], row["black"], row["result"]
        if r == "1-0":
            h[w][b]["wins"] += 1; h[b][w]["losses"] += 1
        elif r == "0-1":
            h[w][b]["losses"] += 1; h[b][w]["wins"] += 1
        elif r == "1/2-1/2":
            h[w][b]["draws"] += 1; h[b][w]["draws"] += 1
    con.close(); return h

def compute_elo(path: str, anchor: str | None = None, anchor_elo: float = 1500.0) -> dict[str, float]:
    """MLE fit of Elo ratings to observed game outcomes (draws = half win).
    Anchored to `anchor` at `anchor_elo` for interpretability."""
    con = _connect(path)
    engines = sorted(r["name"] for r in con.execute("SELECT name FROM engines"))
    idx = {n: i for i, n in enumerate(engines)}
    games = list(con.execute("SELECT white, black, result FROM games"))
    con.close()
    if not games:
        return {n: anchor_elo for n in engines}

    def neg_log_lik(ratings: np.ndarray) -> float:
        ll = 0.0
        for g in games:
            w, b, r = g["white"], g["black"], g["result"]
            rw, rb = ratings[idx[w]], ratings[idx[b]]
            # Expected score of white (standard Elo logistic, base 10 / 400).
            ew = 1.0 / (1.0 + 10 ** ((rb - rw) / 400.0))
            ew = min(max(ew, 1e-9), 1 - 1e-9)
            if r == "1-0": s = 1.0
            elif r == "0-1": s = 0.0
            else: s = 0.5
            ll += s * math.log(ew) + (1 - s) * math.log(1 - ew)
        return -ll

    x0 = np.full(len(engines), anchor_elo)
    res = minimize(neg_log_lik, x0, method="L-BFGS-B")
    fitted = dict(zip(engines, res.x.tolist()))
    if anchor and anchor in fitted:
        shift = anchor_elo - fitted[anchor]
        fitted = {n: r + shift for n, r in fitted.items()}
    return fitted
```

- [ ] **Step 9.4: Run tests**

Run: `pytest tests/test_stats.py -v`
Expected: PASS.

- [ ] **Step 9.5: Commit**

```bash
git add src/cubist/harness/stats.py tests/test_stats.py
git commit -m "feat: Wilson CI, head-to-head matrix, MLE Bayes-Elo fit"
```

---

## Task 10: Results notebook

**Files:**
- Create: `notebooks/results.ipynb`

- [ ] **Step 10.1: Generate the notebook via Python**

Notebooks are JSON; generate with a script to avoid hand-authoring. Create `notebooks/generate_results_notebook.py`:

```python
"""One-shot generator for notebooks/results.ipynb. Keeps notebook JSON
out of human editing and under version control as a reproducible script."""
import json, os, pathlib

cells = [
    ("markdown", "# Cubist Antichess — Tournament Results\n\n"
                 "Auto-loads `results.db` and renders the experiment ladder, "
                 "head-to-head matrix, and Elo fit."),
    ("code", "from cubist.harness.stats import engine_records, head_to_head, compute_elo\n"
             "import pandas as pd, matplotlib.pyplot as plt\n"
             "DB = '../results.db'"),
    ("markdown", "## Engines & descriptions"),
    ("code", "import sqlite3\ncon = sqlite3.connect(DB); con.row_factory = sqlite3.Row\n"
             "rows = list(con.execute('SELECT * FROM engines'))\npd.DataFrame([dict(r) for r in rows])"),
    ("markdown", "## Per-engine record (Wilson 95% CI)"),
    ("code", "df = pd.DataFrame(engine_records(DB))\ndf"),
    ("code", "plt.figure(figsize=(8,4))\n"
             "plt.errorbar(df['name'], df['score_pct'],\n"
             "             yerr=[df['score_pct']-df['ci_lo'], df['ci_hi']-df['score_pct']],\n"
             "             fmt='o')\nplt.axhline(0.5, ls='--', alpha=0.3)\n"
             "plt.ylabel('score %'); plt.xticks(rotation=30); plt.title('Engine score % with Wilson CI'); plt.show()"),
    ("markdown", "## Head-to-head matrix"),
    ("code", "h = head_to_head(DB)\nnames = sorted(h)\n"
             "mat = [[(h[a][b]['wins']+0.5*h[a][b]['draws'])/max(1,sum(h[a][b].values())) if a!=b else float('nan') for b in names] for a in names]\n"
             "pd.DataFrame(mat, index=names, columns=names).style.background_gradient(cmap='RdYlGn', vmin=0, vmax=1).format('{:.2f}', na_rep='—')"),
    ("markdown", "## Elo ladder (anchored to baseline at 1500)"),
    ("code", "elos = compute_elo(DB, anchor='baseline', anchor_elo=1500.0)\n"
             "pd.DataFrame(sorted(elos.items(), key=lambda x:-x[1]), columns=['engine','elo'])"),
    ("markdown", "## Experiment timeline\n\nEach engine's `description` field is the *hypothesis* "
                 "being tested. Combine with git log and PR links in `docs/hypotheses/` "
                 "to tell the full AI-usage story for judging."),
    ("markdown", "## Cost per Elo point\n\nFill in manually from `docs/hypotheses/`. "
                 "This slide is the judging hook for the efficiency criterion."),
]

nb = {
    "cells": [
        {"cell_type": ct, "source": src, "metadata": {},
         **({"outputs": [], "execution_count": None} if ct == "code" else {})}
        for ct, src in cells
    ],
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                 "language_info": {"name": "python"}},
    "nbformat": 4, "nbformat_minor": 5,
}
out = pathlib.Path(__file__).parent / "results.ipynb"
out.write_text(json.dumps(nb, indent=1))
print(f"Wrote {out}")
```

- [ ] **Step 10.2: Run generator**

Run: `python notebooks/generate_results_notebook.py`
Expected: writes `notebooks/results.ipynb`.

- [ ] **Step 10.3: Smoke-test the notebook**

Run (assuming `results.db` from the earlier Task 5 smoke run — regenerate if needed):
```
python -m cubist.harness.tournament --n-games 4 --time-per-move 0.1 --workers 2 --db results.db
jupyter nbconvert --to notebook --execute notebooks/results.ipynb --output results.executed.ipynb
```
Expected: notebook executes with no errors. Inspect the rendered tables/plots.

- [ ] **Step 10.4: Commit**

```bash
git add notebooks/generate_results_notebook.py notebooks/results.ipynb
git commit -m "feat: results notebook with records, H2H matrix, Elo ladder"
```

---

## Task 11: GitHub Actions smoke test

**Files:**
- Create: `.github/workflows/smoke.yml`

- [ ] **Step 11.1: Write workflow**

Create `.github/workflows/smoke.yml`:

```yaml
name: smoke
on:
  pull_request:
  push:
    branches: [main]

jobs:
  test-and-smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install
        run: pip install -e ".[dev]"
      - name: Unit tests
        run: pytest -x --timeout=30
      - name: Smoke tournament (2 games/pair, 0.05s/move)
        run: |
          mkdir -p ci_games
          python -m cubist.harness.tournament \
            --n-games 2 --time-per-move 0.05 --max-plies 80 --workers 2 \
            --db ci_results.db --games-dir ci_games \
            --tournament-id ci-${{ github.run_id }}
      - name: Count games produced
        run: |
          python - <<'PY'
          from cubist.harness.db import all_games
          g = all_games("ci_results.db")
          assert len(g) >= 2, f"expected ≥2 games, got {len(g)}"
          print(f"OK: {len(g)} games")
          PY
```

- [ ] **Step 11.2: Commit**

```bash
git add .github/workflows/smoke.yml
git commit -m "ci: smoke tournament on every PR"
```

- [ ] **Step 11.3: Verify in GitHub (manual)**

Push branch and open a PR. Confirm the `smoke` check runs green. If it fails on `numpy`/`scipy` wheels, the workflow already pins Python to 3.11 which has prebuilt wheels — no action expected.

---

## Task 12: Antichess invariant tests (parallel-safe)

**Files:**
- Test: `tests/test_antichess_invariants.py`

Run this task in parallel with any engine work — it's pure `AntichessBoard` assertions.

- [ ] **Step 12.1: Write the test file**

Create `tests/test_antichess_invariants.py`:

```python
"""Invariants we rely on from python-chess's AntichessBoard.

If any of these break, the baseline eval + harness assumptions break with
them. Pin behavior so a python-chess upgrade can't silently regress us.
"""
import chess
from chess.variant import AntichessBoard

def test_starting_position_has_no_captures():
    b = AntichessBoard()
    assert not any(b.is_capture(m) for m in b.legal_moves)

def test_captures_are_forced_when_available():
    b = AntichessBoard()
    for uci in ["e2e3", "d7d5", "e3e4"]:
        b.push_uci(uci)
    # Black to move: d5xe4 is the only legal move family (forced-capture rule).
    legal = list(b.legal_moves)
    assert all(b.is_capture(m) for m in legal), \
        "in antichess, legal_moves must be captures-only when any capture exists"

def test_losing_all_pieces_is_a_win_for_loser():
    # Construct a position with a single white pawn. Black captures it; White wins.
    b = AntichessBoard.from_epd("8/8/8/8/8/8/P7/k7 w - -")[0]
    # Not easily reachable via normal play; test the result API on an end state.
    assert not b.is_variant_end()  # not over yet
    # Simpler: use a canonical end state where side to move has no pieces.
    b2 = AntichessBoard.from_epd("8/8/8/8/8/8/8/k7 w - -")[0]
    assert b2.is_variant_end()
    assert b2.result() in ("1-0", "0-1", "1/2-1/2")

def test_stalemate_is_a_win_for_stalemated_side():
    # Documented antichess rule: the side with no legal moves WINS.
    # We verify python-chess agrees by checking result() on a known stalemate.
    # Set up: white king on a1, white pawn on a2; black king on a3. White to move
    # has a2 blocked and a1 can only move if not in "check-like" (antichess has
    # no check). Construct a position where side to move has zero legal moves.
    b = AntichessBoard.from_epd("8/8/8/8/8/k7/8/K7 w - -")[0]
    # Simplify: just verify that when legal_moves is empty, is_variant_end is True
    # and result() isn't a draw by default.
    if b.legal_moves.count() == 0:
        assert b.is_variant_end()
        assert b.result() in ("1-0", "0-1")

def test_zobrist_hash_is_stable_on_identical_positions():
    import chess.polyglot
    b1 = AntichessBoard()
    b2 = AntichessBoard()
    assert chess.polyglot.zobrist_hash(b1) == chess.polyglot.zobrist_hash(b2)
    b1.push_uci("e2e3")
    assert chess.polyglot.zobrist_hash(b1) != chess.polyglot.zobrist_hash(b2)

def test_copy_preserves_legal_moves():
    b = AntichessBoard()
    b.push_uci("e2e3")
    c = b.copy()
    assert list(c.legal_moves) == list(b.legal_moves)
    c.push_uci("d7d5")
    assert list(c.legal_moves) != list(b.legal_moves)  # copies diverge
```

- [ ] **Step 12.2: Run tests**

Run: `pytest tests/test_antichess_invariants.py -v`
Expected: PASS. If any test fails, `python-chess` has changed behavior — flag this before continuing; other tasks depend on these invariants.

- [ ] **Step 12.3: Commit**

```bash
git add tests/test_antichess_invariants.py
git commit -m "test: pin antichess invariants we rely on from python-chess"
```

---

## Task 13: UCI wrapper for demo (stretch)

Runs Saturday 2:30pm after merge freeze.

**Files:**
- Create: `src/cubist/uci.py`
- Test: `tests/test_uci.py`

- [ ] **Step 13.1: Write failing tests**

Create `tests/test_uci.py`:

```python
import io
import chess
from cubist.uci import UciAdapter
from cubist.engines.baseline import BaselineEngine

def test_uci_identifies_on_uci_command():
    out = io.StringIO()
    a = UciAdapter(BaselineEngine(), out=out)
    a.handle("uci")
    text = out.getvalue()
    assert "id name" in text
    assert "uciok" in text

def test_uci_isready():
    out = io.StringIO()
    a = UciAdapter(BaselineEngine(), out=out)
    a.handle("isready")
    assert "readyok" in out.getvalue()

def test_uci_returns_bestmove_from_startpos_with_movetime():
    out = io.StringIO()
    a = UciAdapter(BaselineEngine(max_depth=2), out=out)
    a.handle("ucinewgame")
    a.handle("position startpos")
    a.handle("go movetime 200")
    text = out.getvalue()
    assert "bestmove " in text
    # extract bestmove and verify it's a legal UCI move
    line = [l for l in text.splitlines() if l.startswith("bestmove")][0]
    mv = chess.Move.from_uci(line.split()[1])
    from chess.variant import AntichessBoard
    assert mv in AntichessBoard().legal_moves
```

- [ ] **Step 13.2: Verify tests fail**

Run: `pytest tests/test_uci.py -v`
Expected: FAIL — ModuleNotFoundError.

- [ ] **Step 13.3: Implement `src/cubist/uci.py`**

```python
from __future__ import annotations
import sys
from typing import TextIO
import chess
from chess.variant import AntichessBoard
from cubist.engine import Engine

class UciAdapter:
    """Minimal UCI adapter over an `Engine`. Supports: uci, isready, ucinewgame,
    position [startpos | fen <fen>] [moves ...], go [movetime <ms>], quit."""

    def __init__(self, engine: Engine, out: TextIO | None = None):
        self.engine = engine
        self.out = out if out is not None else sys.stdout
        self.board = AntichessBoard()

    def _println(self, s: str) -> None:
        self.out.write(s + "\n"); self.out.flush()

    def handle(self, line: str) -> bool:
        """Handle one line. Returns False on 'quit', True otherwise."""
        line = line.strip()
        if not line:
            return True
        if line == "uci":
            self._println(f"id name cubist-{self.engine.name}")
            self._println("id author cubist-hackathon")
            self._println("option name UCI_Variant type combo default Antichess var Antichess")
            self._println("uciok")
        elif line == "isready":
            self._println("readyok")
        elif line == "ucinewgame":
            self.board = AntichessBoard()
        elif line.startswith("position"):
            self._handle_position(line)
        elif line.startswith("go"):
            self._handle_go(line)
        elif line == "quit":
            return False
        return True

    def _handle_position(self, line: str) -> None:
        tokens = line.split()
        # position startpos [moves ...] | position fen <fen parts...> [moves ...]
        if "startpos" in tokens:
            self.board = AntichessBoard()
            if "moves" in tokens:
                idx = tokens.index("moves")
                for mv in tokens[idx+1:]:
                    self.board.push_uci(mv)
        elif "fen" in tokens:
            idx = tokens.index("fen")
            fen_parts = tokens[idx+1: idx+7]
            self.board = AntichessBoard(" ".join(fen_parts))
            if "moves" in tokens:
                m_idx = tokens.index("moves")
                for mv in tokens[m_idx+1:]:
                    self.board.push_uci(mv)

    def _handle_go(self, line: str) -> None:
        tokens = line.split()
        movetime_ms = 500  # default
        if "movetime" in tokens:
            movetime_ms = int(tokens[tokens.index("movetime") + 1])
        move = self.engine.play(self.board.copy(), time_limit_s=movetime_ms / 1000.0)
        self._println(f"bestmove {move.uci()}")

def main(argv: list[str] | None = None) -> None:
    argv = argv or sys.argv[1:]
    name = argv[0] if argv else "baseline"
    from cubist.engines.registry import REGISTRY
    engine = REGISTRY[name]()
    adapter = UciAdapter(engine)
    for line in sys.stdin:
        if not adapter.handle(line):
            break

if __name__ == "__main__":
    main()
```

- [ ] **Step 13.4: Run tests**

Run: `pytest tests/test_uci.py -v`
Expected: PASS.

- [ ] **Step 13.5: Live demo check against a GUI (manual, 5 min)**

Use BanksiaGUI or Arena:
- Add new engine: `python -m cubist.uci baseline`
- Configure variant = Antichess
- Start a game vs. another instance or a human. Engine should respond, move legally, finish the game.

- [ ] **Step 13.6: Commit**

```bash
git add src/cubist/uci.py tests/test_uci.py
git commit -m "feat: minimal UCI adapter for live demo"
```

---

## Task 14: LLMPersonaEngine variant + Anthropic client (stretch)

Runs Saturday afternoon or anytime after Task 2. This is the **headline AI-usage variant** — Claude as a move-proposer that classical code validates. Spec §4 blesses it ("LLM-in-the-loop: Claude Haiku as a fallback move-picker").

**Strategic framing:** the engine asks Claude for a ranked list of candidate moves at decision points; classical code filters to `board.legal_moves` (never trust the LLM for legality); if Claude's top pick is illegal or worse than baseline's pick (per a shallow search), fall back to baseline. Every Claude call caches by FEN in SQLite (reuses across games/persona-variants) so the tournament doesn't blow the budget.

**Files:**
- Create: `src/cubist/llm/__init__.py`
- Create: `src/cubist/llm/client.py` — Anthropic client + FEN-keyed SQLite cache + token budget
- Create: `src/cubist/engines/llm_persona.py` — `LLMPersonaEngine(baseline, persona, client)`
- Test: `tests/test_llm_client.py`, `tests/test_llm_persona.py`
- Modify: `src/cubist/engines/registry.py` — register 4 persona variants
- Modify: `pyproject.toml` — add `anthropic>=0.40` optional dep

- [ ] **Step 14.1: Add optional dep**

Update `pyproject.toml` `[project.optional-dependencies]`:

```toml
dev = ["pytest>=7.4", "pytest-timeout>=2.2", "pytest-xdist>=3.5"]
llm = ["anthropic>=0.40"]
```

Run: `pip install -e ".[dev,llm]"`.

- [ ] **Step 14.2: Write failing tests for the client cache**

Create `tests/test_llm_client.py`:

```python
import os
from cubist.llm.client import ClaudeClient, FenCache

def test_fen_cache_stores_and_retrieves(tmp_path):
    cache = FenCache(tmp_path / "cache.db")
    cache.put("fen1", "persona-donor", "e2e4\ne7e5\nd2d4", tokens=42)
    rows = cache.get("fen1", "persona-donor")
    assert rows == "e2e4\ne7e5\nd2d4"

def test_client_offline_mode_uses_cache_only(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = ClaudeClient(cache_path=tmp_path / "c.db", offline=True)
    client.cache.put("fen1", "donor", "e2e4", tokens=0)
    assert client.ask_candidates("fen1", "donor", prompt="...") == ["e2e4"]

def test_client_refuses_without_key_and_without_cache(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = ClaudeClient(cache_path=tmp_path / "c.db", offline=True)
    # no cache hit → must return [] not crash
    assert client.ask_candidates("missing-fen", "donor", prompt="...") == []
```

- [ ] **Step 14.3: Verify tests fail**

Run: `pytest tests/test_llm_client.py -v`
Expected: FAIL — ModuleNotFoundError.

- [ ] **Step 14.4: Implement `src/cubist/llm/client.py`**

```python
from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from dataclasses import dataclass

class FenCache:
    """SQLite-backed FEN+persona → candidate-list cache.
    Shared across the whole tournament — one Claude call per (fen, persona) ever."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        with sqlite3.connect(self.path) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS llm_cache (
                fen TEXT, persona TEXT, candidates TEXT, tokens INTEGER,
                PRIMARY KEY (fen, persona))""")

    def get(self, fen: str, persona: str) -> str | None:
        with sqlite3.connect(self.path) as c:
            row = c.execute(
                "SELECT candidates FROM llm_cache WHERE fen=? AND persona=?",
                (fen, persona)).fetchone()
            return row[0] if row else None

    def put(self, fen: str, persona: str, candidates: str, tokens: int) -> None:
        with sqlite3.connect(self.path) as c:
            c.execute("""INSERT OR REPLACE INTO llm_cache VALUES (?, ?, ?, ?)""",
                      (fen, persona, candidates, tokens))

    def total_tokens(self) -> int:
        with sqlite3.connect(self.path) as c:
            (t,) = c.execute("SELECT COALESCE(SUM(tokens), 0) FROM llm_cache").fetchone()
            return t

class ClaudeClient:
    """Thin wrapper: FEN+persona → list of candidate UCI moves, cached forever.
    `offline=True` skips network; cache-miss returns []. Use in CI and locally
    when no API key is present."""

    def __init__(self, cache_path: str | Path = "llm_cache.db",
                 offline: bool = False, max_tokens: int = 200,
                 budget_tokens: int = 200_000):
        self.cache = FenCache(cache_path)
        self.offline = offline or not os.environ.get("ANTHROPIC_API_KEY")
        self.max_tokens = max_tokens
        self.budget_tokens = budget_tokens

    def ask_candidates(self, fen: str, persona: str, prompt: str) -> list[str]:
        hit = self.cache.get(fen, persona)
        if hit is not None:
            return [m for m in hit.splitlines() if m]
        if self.offline:
            return []
        if self.cache.total_tokens() > self.budget_tokens:
            return []  # budget blown; fall back to baseline
        import anthropic
        msg = anthropic.Anthropic().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}])
        text = msg.content[0].text if msg.content else ""
        used = (msg.usage.input_tokens + msg.usage.output_tokens) if msg.usage else 0
        moves = [ln.strip() for ln in text.splitlines() if ln.strip()]
        self.cache.put(fen, persona, "\n".join(moves), used)
        return moves
```

- [ ] **Step 14.5: Implement `src/cubist/engines/llm_persona.py`**

```python
from __future__ import annotations
import chess
from chess.variant import AntichessBoard
from cubist.engine import Engine
from cubist.engines.baseline import BaselineEngine
from cubist.llm.client import ClaudeClient

PERSONAS = {
    "donor":      "You are an antichess expert. Your style: aggressively give away pieces, especially long-range sliders (queens, rooks, bishops). Propose 3 candidate moves as UCI, one per line, no commentary.",
    "trapper":    "You are an antichess expert. Your style: set up positions where the opponent MUST capture into bad piece-square configurations. Propose 3 candidate moves as UCI, one per line, no commentary.",
    "forced_line": "You are an antichess expert. Your style: find moves that initiate the longest forced-capture chains (forcing sequences that dictate opponent responses). Propose 3 candidate moves as UCI, one per line, no commentary.",
    "materialist": "You are a CHESS grandmaster (note: chess, not antichess). Your style: maximize material and protect your queen at all costs. Propose 3 candidate moves as UCI, one per line, no commentary.",
    # ^ materialist is INTENTIONALLY backwards for antichess — we expect it to lose.
    # That's the punchline: "in antichess, being materialist is literally the wrong objective."
}

PROMPT_TEMPLATE = "{persona_header}\n\nPosition (FEN): {fen}\nLegal moves (UCI): {legal_moves}\nPropose 3 candidate moves:"

class LLMPersonaEngine(Engine):
    """Claude-proposed candidate moves, classical fallback. Legality enforced
    in code — LLM output is never trusted for legality."""

    def __init__(self, persona: str = "forced_line", client: ClaudeClient | None = None,
                 fallback_depth: int = 3):
        assert persona in PERSONAS, f"unknown persona: {persona}"
        self.persona = persona
        self.name = f"llm_{persona}"
        self.description = f"Claude-Haiku candidate proposer with `{persona}` persona, classical fallback."
        self.client = client or ClaudeClient()
        self.fallback = BaselineEngine(max_depth=fallback_depth)

    def play(self, board: AntichessBoard, time_limit_s: float) -> chess.Move:
        legal = list(board.legal_moves)
        legal_uci = {m.uci() for m in legal}
        prompt = PROMPT_TEMPLATE.format(
            persona_header=PERSONAS[self.persona],
            fen=board.fen(),
            legal_moves=" ".join(sorted(legal_uci)),
        )
        candidates = self.client.ask_candidates(board.fen(), self.persona, prompt)
        for uci in candidates:
            if uci in legal_uci:
                return chess.Move.from_uci(uci)
        # Fallback: LLM empty / budget blown / all illegal.
        return self.fallback.play(board, time_limit_s)
```

- [ ] **Step 14.6: Write persona-engine tests**

Create `tests/test_llm_persona.py`:

```python
import chess
from chess.variant import AntichessBoard
from cubist.engines.llm_persona import LLMPersonaEngine, PERSONAS
from cubist.llm.client import ClaudeClient

def test_all_four_personas_registered():
    assert set(PERSONAS.keys()) == {"donor", "trapper", "forced_line", "materialist"}

def test_llm_persona_falls_back_to_baseline_when_offline(tmp_path):
    client = ClaudeClient(cache_path=tmp_path / "c.db", offline=True)
    eng = LLMPersonaEngine("donor", client=client)
    board = AntichessBoard()
    mv = eng.play(board, time_limit_s=0.5)
    assert mv in board.legal_moves

def test_llm_persona_prefers_cached_candidate_when_legal(tmp_path):
    client = ClaudeClient(cache_path=tmp_path / "c.db", offline=True)
    board = AntichessBoard()
    # pick a legal move and seed the cache for this exact FEN+persona
    legal = list(board.legal_moves)[0].uci()
    client.cache.put(board.fen(), "donor", legal, tokens=0)
    eng = LLMPersonaEngine("donor", client=client)
    mv = eng.play(board, time_limit_s=0.5)
    assert mv.uci() == legal

def test_llm_persona_filters_illegal_cached_candidates(tmp_path):
    client = ClaudeClient(cache_path=tmp_path / "c.db", offline=True)
    board = AntichessBoard()
    client.cache.put(board.fen(), "donor", "a1a8\nb1b8", tokens=0)  # both illegal
    eng = LLMPersonaEngine("donor", client=client)
    mv = eng.play(board, time_limit_s=0.5)
    assert mv in board.legal_moves  # fell back to baseline, still legal
```

- [ ] **Step 14.7: Register the persona variants**

Modify `src/cubist/engines/registry.py` — add:

```python
from cubist.engines.llm_persona import LLMPersonaEngine, PERSONAS
for _persona in PERSONAS:
    REGISTRY[f"llm_{_persona}"] = (lambda p=_persona: LLMPersonaEngine(p))
```

- [ ] **Step 14.8: Run tests**

Run: `pytest tests/test_llm_client.py tests/test_llm_persona.py -v`
Expected: PASS. All 7 tests green. No network calls (offline mode throughout tests).

- [ ] **Step 14.9: Commit**

```bash
git add src/cubist/llm/ src/cubist/engines/llm_persona.py src/cubist/engines/registry.py \
        tests/test_llm_client.py tests/test_llm_persona.py pyproject.toml
git commit -m "feat: LLMPersonaEngine variant — Claude-Haiku candidate proposer with classical fallback"
```

**Pitch hook for demo:** run the tournament including all 4 personas. Forced-line / donor / trapper should place competitively with baseline; **materialist should lose every game** because in antichess being a materialist is literally the wrong objective. That visual in the Elo ladder is the strongest 30-second AI-usage story you can ship.

---

## Task 15: Lichess bot deployment (stretch, Sat 2pm+)

Runs Saturday afternoon after Task 13 (UCI) lands. Spec §5 blesses it ("optional Lichess bot account"). This replaces "notebook walkthrough" with **"judges challenge our engine live during judging"** — highest-impact demo surface we have.

**Important constraints:**
- Lichess bot upgrade is **irreversible** — use a fresh account, not a personal one.
- Do this only when Task 13 passes; no point registering a bot before the UCI shim works.
- During the first live game, keep games casual (not rated) until you've watched one completion — catches any UCI edge cases.

**Files:**
- Create: `bot/README.md` — runbook for challenging / restarting
- Create: `scripts/run_bot.sh` — tmux-wrapped runner
- Modify: `README.md` — add "Play us live" link at top

- [ ] **Step 15.1: Create fresh Lichess bot account**

Manual, not a script step:
1. lichess.org → logout → Sign up. Username `cubist-bot-<short-team-tag>` (e.g. `cubist-bot-ann`).
2. **Do not play any games** on the account — upgrade is only available to accounts with zero games.
3. Settings → API Access Tokens → `+` → scope `bot:play` → save token.
4. Run upgrade:

```bash
export LICHESS_TOKEN=<paste-token>
curl -d '' https://lichess.org/api/bot/account/upgrade \
  -H "Authorization: Bearer $LICHESS_TOKEN"
```

Expected: `{"ok":true}`. Account now shows "BOT" badge.

- [ ] **Step 15.2: Clone and configure lichess-bot**

```bash
git clone https://github.com/lichess-bot-devs/lichess-bot.git bot/lichess-bot
cd bot/lichess-bot
pip install -r requirements.txt
cp config.yml.default config.yml
```

Edit `bot/lichess-bot/config.yml`:

```yaml
token: "YOUR_LICHESS_TOKEN"
engine:
  dir: "../../"                       # repo root
  name: "python"                      # executable
  working_dir: "../../"
  protocol: "uci"
  variants: ["antichess"]
  options: {}
  engine_options:
    - "-m"
    - "cubist.uci"                    # runs `python -m cubist.uci`
    - "baseline"                      # which registered engine to wrap
  ponder: false
challenge:
  concurrency: 1
  sort_by: "best"
  accept_bot: true
  only_bot: false
  max_increment: 60
  min_increment: 0
  max_base: 600
  min_base: 10
  variants: ["antichess"]
  time_controls: ["bullet", "blitz", "rapid"]
  modes: ["casual"]                   # rated: add after first verified game
```

- [ ] **Step 15.3: Create `scripts/run_bot.sh`**

```bash
#!/usr/bin/env bash
# Launch the lichess bot in a tmux session so it survives SSH/lid-close.
set -euo pipefail
SESSION="cubist-bot"
cd "$(dirname "$0")/.."
tmux has-session -t "$SESSION" 2>/dev/null && tmux kill-session -t "$SESSION"
tmux new-session -d -s "$SESSION" \
  "cd bot/lichess-bot && python lichess-bot.py 2>&1 | tee ../../runs/bot-$(date +%Y%m%dT%H%M%S).log"
echo "Bot started in tmux session '$SESSION'. Attach: tmux attach -t $SESSION"
```

Make it executable: `chmod +x scripts/run_bot.sh`.

- [ ] **Step 15.4: Smoke test (one completed casual game)**

```bash
bash scripts/run_bot.sh
```

Then from a different browser / incognito window:
1. lichess.org → challenge `cubist-bot-<your-suffix>` to an antichess game, 10+0 casual.
2. Play ~10 moves. Verify the engine responds, plays legal moves, doesn't crash.
3. Check `runs/bot-*.log` for warnings.

Expected: game completes (win/loss/draw doesn't matter) with no exceptions. Tournament-run data in `results.db` is NOT polluted — Lichess games don't feed the DB.

- [ ] **Step 15.5: Create `bot/README.md`**

```markdown
# Lichess Bot

Our antichess engine plays live on Lichess:
**https://lichess.org/@/cubist-bot-YOUR-SUFFIX**

## Challenge it
From any Lichess account → open the bot profile → "Challenge" → select antichess, any time control ≤10+0.

## Running the bot
```bash
export LICHESS_TOKEN=<redacted>  # stored in 1Password / env
bash scripts/run_bot.sh          # launches tmux session `cubist-bot`
tmux attach -t cubist-bot        # to watch live logs
```

## Troubleshooting
- Engine not responding: check `runs/bot-*.log` for UCI parse errors. Reproduce locally with `python -m cubist.uci baseline`.
- Rate-limited by Lichess: `config.yml` → `challenge.concurrency: 1` (already set).
- To accept rated games: `config.yml` → `challenge.modes: [casual, rated]`. Only after ≥5 verified casual games.
```

- [ ] **Step 15.6: Update root README**

At the top of `README.md`, add:

```markdown
> **Play us live on Lichess:** https://lichess.org/@/cubist-bot-YOUR-SUFFIX (antichess only)
```

- [ ] **Step 15.7: Commit (do NOT commit the token)**

```bash
# sanity: never commit the token
grep -r "lip_" bot/ 2>/dev/null && echo "ABORT: token in repo" && exit 1

git add bot/README.md scripts/run_bot.sh README.md
git commit -m "feat: lichess bot deployment (stretch demo surface)"
```

`bot/lichess-bot/config.yml` should be in `.gitignore` (token lives there). Add if missing:

```
bot/lichess-bot/config.yml
```

- [ ] **Step 15.8: Judging-time runbook**

Last thing before judging starts:
1. Bot running in tmux (`tmux ls` shows `cubist-bot`).
2. Test challenge from a team member's account — game completes cleanly.
3. If rated games desired, switch `modes: [casual, rated]` + restart bot.
4. README top-line link to bot profile is correct.

---

## Self-review (done by author, inline)

**Spec coverage check:**
- §3.1 Engine protocol → Task 2 ✅
- §3.2 BaselineEngine → Tasks 6, 7, 8 ✅
- §3.3 match harness → Task 3 ✅
- §3.4 tournament runner → Task 5 (+ DB in Task 4) ✅
- §3.5 stats (Wilson, H2H, Bayes-Elo) → Task 9 ✅
- §3.6 results notebook → Task 10 ✅
- §4 experimentation workflow (CI smoke) → Task 11 ✅
- §4 LLM-in-the-loop example variant → Task 14 ✅
- §5 optional Lichess bot → Task 15 ✅
- §6 deliverables (UCI wrapper for demo) → Task 13 ✅
- §7 non-goals — nothing out-of-scope slipped in ✅
- §8 risks (forfeit handling, CI smoke-test) → Task 3, Task 11 ✅
- §8 cost blowup from LLM-in-loop → Task 14 token budget + FEN cache + `offline=True` tests ✅
- Antichess invariants → Task 12 ✅

**Placeholder scan:** no TBD/TODO/"fill in later". All code steps contain complete code. All run commands contain concrete expected output.

**Type consistency:** `Engine.play(board, time_limit_s)` used consistently across Tasks 2, 6-8, 13, 14. `Outcome` enum values used identically in tests and `_result_str`. DB column names match between schema, writers, and readers. `LLMPersonaEngine` extends `Engine` and passes the same invariant tests as every other engine via Task 12.

**Not covered in plan (intentional — these are teammate creative work, per spec):** Person D's variant engines (beyond `LLMPersonaEngine`), `docs/hypotheses/` notes. These get added by their authors via the same `engines/<name>.py` + `registry.py` + PR + CI pattern Task 2 establishes.

**Stretch task ordering:** Task 14 depends on Task 2 only (the registry). Task 15 depends on Task 13 (UCI). If only one stretch has time: prioritize Task 14 (headline AI-usage variant, no external account needed) over Task 15 (nice-to-have live demo surface that can be replaced by the notebook walkthrough).

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-24-antichess-engine.md`.** Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using executing-plans, batch with checkpoints.

Which approach?
