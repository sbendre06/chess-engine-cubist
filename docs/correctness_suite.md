# Hidden Antichess Correctness Suite

A three-tier objective rubric for the Cubist ablation experiment. Every engine in `engines/` is scored against curated FEN positions; results land in `evaluation/results/correctness/<engine>.json` and feed three new columns in `experiment_log.csv` (`tier0_pass_rate`, `tier1_pass_rate`, `tier2_pass_rate`).

The three tiers test different things:

| Tier | Count | What it measures | How |
|---|---|---|---|
| **Tier 0** | 50 | Broad correctness coverage on typical positions | Random-walk sample, deterministic seed; each fixture asserts engine's filtered pseudo-legal output ⊇ `board.legal_moves` |
| **Tier 1** | 14 | Targeted antichess-vs-standard-chess prior conflicts | Hand-curated edge cases (forced capture, no castling, promotion-to-king, stalemate-as-win, king-attacked-but-quiet-moves-legal, etc.) |
| **Tier 2** | 7 | Strategic decision quality at fixed search depth | Watkins-derived openings, pawn-push endgames, forced-win positions; engine drives `iterative_deepening` and the chosen root move is checked against an `expected_moves` set |

## How to run

```bash
.venv/bin/python -m evaluation.correctness --engine baseline       # single engine
.venv/bin/python -m evaluation.correctness --all --depth 4         # full ablation matrix
.venv/bin/python -m evaluation.correctness --validate-fixtures     # FEN sanity check
.venv/bin/python -m evaluation.correctness --all --json            # machine-readable
.venv/bin/python -m evaluation.correctness_matrix                  # rendered pass/fail table
.venv/bin/python -m evaluation.correctness_plot                    # heatmap PNG
```

## Architectural assumptions

The suite calls each engine through its **Core 3** primitives, the frozen contract enforced by `harness/loader.py:8` for every engine in the project:

```
get_pseudo_legal_moves(board) -> list[chess.Move]
evaluate_board(board)         -> int   # side-to-move-positive (negamax convention)
order_moves(board, moves)     -> list[chess.Move]
```

Two ground rules shape what is and isn't testable:

1. **The harness already filters illegal moves.** `harness/engine.py:106` runs `[m for m in candidates if m in board.legal_moves]` before any move is played. That means engines literally cannot play illegal moves in real matches — so the suite isn't catching cheaters; it's surfacing whether the engine *itself* understands the rules, independent of the safety net.
2. **`chess.variant.AntichessBoard` enforces Giveaway rules.** Forced capture, no castling, king-capturable, promotion-to-king, and stalemate-as-win-for-stalemated-side are all built in. Engines that delegate to `board.legal_moves` get those for free.

## Tier 0 — Broad Correctness Coverage

50 positions sampled by random-legal-move walks from the standard antichess starting position. Generation is deterministic (`RANDOM_WALK_SEED = 42`), so the corpus is stable across runs.

Each fixture uses the `move_gen_superset` rule: the engine's filtered pseudo-legal output must contain every move in `board.legal_moves` (no legal move dropped). This is the most basic correctness signal — "does the engine's move generator agree with python-chess on a typical board?"

Sample distribution:
- Ply depth: 5–30 (avg ~15)
- Legal-move count per position: 1–41
- Mix of forced-capture and open positions, plus a few near-endgame positions

Test IDs: `random_walk_00` through `random_walk_49`.

Currently every engine passes all 50 Tier 0 tests. That's expected — every engine in the project delegates move generation to `chess.variant.AntichessBoard.pseudo_legal_moves` (or its filtered cousin), which by construction agrees with `board.legal_moves`. The narrative this enables: **"every engine handles 50 random positions correctly. The differential only appears on hand-crafted prior-conflict edge cases (Tier 1) and strategic depth (Tier 2)."**

If a future engine implements its own move generator from scratch, Tier 0 is where bugs would surface first.

## Tier 1 — Targeted Rule Compliance

Calls Core 3 primitives directly on a curated position. No search. Eight rule types:

| Rule | What it asserts |
|---|---|
| `move_gen_superset` | engine's filtered pseudo-legal output ⊇ `board.legal_moves` (no legal moves dropped) |
| `legal_moves_exact` | engine's filtered pseudo-legal output **equals** an explicit set (catches "polluting" generators) |
| `contains_moves` | engine's pseudo-legal output includes specific UCIs |
| `excludes_moves` | engine's pseudo-legal output does **not** include specific UCIs |
| `eval_winning` | `evaluate_board(board) >= expected.min_score` |
| `eval_losing` | `evaluate_board(board) <= expected.max_score` |
| `terminal_winner` | `board.outcome().winner` matches expected color |
| `not_terminal` | `board.is_game_over()` is False |

### The 14 Tier 1 fixtures

#### Move generation

- **`move_gen_completeness_startpos`** (`move_gen_superset`)
  - **FEN:** standard starting position
  - **What it tests:** engine doesn't drop any legal move from the search frontier. The harness silently discards illegal candidates but does NOT add legal moves the engine missed — so a buggy generator can starve the search of options.

- **`forced_capture_exact_set`** (`legal_moves_exact`)
  - **FEN:** `4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1` (white pawn e4 vs black pawn d5)
  - **Expected legal:** `{e4d5}`
  - **What it tests:** the forced-capture rule eliminates all quiet moves. Engine's filtered set must equal exactly `{e4d5}` — no king moves, no pawn pushes. Catches engines whose generator includes quiet moves alongside the capture (silently filtered by the harness, but indicates the engine doesn't understand the rule).

- **`multi_capture_exact_set`** (`legal_moves_exact`)
  - **FEN:** `4k3/8/8/8/p3Q2p/8/8/4K3 w - - 0 1` (queen e4, pawns a4 + h4 + king e8 reachable)
  - **Expected legal:** `{e4a4, e4h4, e4e8}` — exactly three captures
  - **What it tests:** all available captures are surfaced; no quiet moves slip through. Stronger than "contains a capture."

- **`king_capturable_exact_set`** (`legal_moves_exact`)
  - **FEN:** `8/8/8/4k3/3Q4/8/8/4K3 w - - 0 1` (white queen d4, black king en prise on e5)
  - **Expected legal:** `{d4e5}`
  - **What it tests:** the no-check rule. Engine must offer Qxe5 with no quiet alternatives. Catches engines that "protect" against king-capture or refuse to generate it as a candidate.

- **`promotion_to_king_offered`** (`contains_moves`)
  - **FEN:** `4k3/P7/8/8/8/8/8/4K3 w - - 0 1` (white pawn on a7)
  - **Required:** `{a7a8k, a7a8q}`
  - **What it tests:** antichess allows promotion to king. Engine must offer `a7a8k` alongside the standard promotions. A naive port of standard chess would drop king-promotion.

#### Castling (split by side)

- **`no_castling_white`** (`excludes_moves`)
  - **FEN:** `r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1`, white to move
  - **Forbidden:** `{e1g1, e1c1}`
  - **What it tests:** even with full castling rights in the FEN, antichess bans castling. Engine must not offer castling moves on white's turn.

- **`no_castling_black`** (`excludes_moves`)
  - Same FEN, black to move; forbidden `{e8g8, e8c8}`.
  - **Why split:** the original combined version had black-side moves listed as forbidden on white's turn — a sloppy no-op. Splitting forces both halves of the assertion to actually fire.

#### Terminal-state recognition

- **`terminal_no_pieces_is_win`** (`terminal_winner`)
  - **FEN:** `8/8/8/8/8/8/8/4K3 b - - 0 1` (black has 0 pieces, black to move)
  - **Expected winner:** black
  - **What it tests:** antichess wins by reducing your piece count to zero. `board.outcome().winner` must be `BLACK` (the side at zero), inverting standard chess intuition.

- **`stalemate_is_win_for_stalemated`** (`terminal_winner`)
  - **FEN:** `8/8/8/8/8/p7/P7/8 b - - 0 1` (black pawn a3 blocked by white a2; no captures, no quiet moves)
  - **Expected winner:** black
  - **What it tests:** Giveaway rules — stalemated side wins. Confirms python-chess's `is_variant_win` treats stalemate-no-legal-moves as a win for the side to move.

- **`checkmate_not_terminal`** (`not_terminal`)
  - **FEN:** Fool's mate position (`rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3`)
  - **What it tests:** standard chess scores this as black wins by checkmate. Antichess has no check rule → 19 legal moves remain. `board.is_game_over()` must be False. Catches engines (or game loops) that piggyback on standard chess's checkmate detection.

#### Adversarial — antichess inverts standard-chess priors

- **`king_attacked_quiet_moves_remain_legal`** (`contains_moves`)
  - **FEN:** `4q3/8/8/8/8/8/4K2P/8 w - - 0 1` (white king e1 "attacked" by black queen e8)
  - **Required:** `{h2h3, h2h4}`
  - **What it tests:** quiet moves that *don't address the threat* must remain legal. Standard chess would force a check-evasion; antichess doesn't recognize check at all. Catches engines that filter "unsafe" quiet moves.

- **`must_capture_even_if_self_destructive`** (`legal_moves_exact`)
  - **FEN:** `4q3/8/8/8/8/8/8/4Q3 w - - 0 1` (white queen e1, black queen e8 — only legal move is Qxe8)
  - **Expected legal:** `{e1e8}`
  - **What it tests:** Qxe8 leaves white with one piece and black with zero → black wins next ply. Standard-chess intuition says "don't make a capture that loses the game"; antichess's forced-capture rule overrides that. Engine must offer the move with no quiet alternatives.

#### Inverted material evaluation

- **`inverted_material_white_winning`** (`eval_winning`)
  - **FEN:** `3qk3/8/8/8/8/8/8/4K3 w - - 0 1` (white K vs black K+Q; white = fewer pieces = winning)
  - **Min score:** `1` (positive)
  - **What it tests:** `evaluate_board` must reflect "fewer of my pieces = better." This is **not** an arbitrary convention — `harness/engine.py:151` does `score = -_negamax(...)`, which bakes in side-to-move-positive eval. An engine returning negative here would lose every game by minimizing instead of maximizing.

- **`inverted_material_white_losing`** (`eval_losing`)
  - **FEN:** `4k3/8/8/8/8/8/8/3QK3 w - - 0 1` (white K+Q vs black K)
  - **Max score:** `-1` (negative)
  - Symmetric to the above; catches engines using standard chess material values.

## Tier 2 — Strategic Decision Quality

Drives `harness.engine.iterative_deepening` at fixed depth. Inspects the chosen root move and checks membership in an `expected_moves` set. Multiple acceptable moves per fixture (transposition-tolerant).

### The 7 Tier 2 fixtures

- **`forced_single_move`** (depth 2)
  - **FEN:** `4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1` (only legal move is `e4d5`)
  - **Expected:** `{e4d5}`
  - Sanity test — search must return the only legal move regardless of depth.

- **`opening_e3_or_central_pawn`** (depth 3)
  - **FEN:** standard starting position
  - **Expected:** `{e2e3, e2e4, d2d3, d2d4}`
  - **Source:** Watkins (1.e3 weakly solves antichess for white).
  - **Notes:** lenient — accepts any central pawn opening, not strictly `e2e3`. Five of ten engines fail this; depth-4 alpha-beta plausibly can't rediscover Watkins's line from a 200-core-year proof tree, so failure here is informative rather than damning.

- **`liardet_a4_or_pawn_response`** (depth 3)
  - **FEN:** `rnbqkbnr/p1pppppp/1p6/8/8/4P3/PPPP1PPP/RNBQKBNR w KQkq - 0 2` (after 1.e3 b6)
  - **Expected:** `{a2a4, a2a3, b2b3, c2c4, c2c3}`
  - **Source:** Watkins (Liardet defense; switching to 2.a4 in May 2015 was the breakthrough that broke the line).

- **`kp_endgame_push_pawn`** (depth 4)
  - **FEN:** `4k3/8/8/8/8/8/P7/4K3 w - - 0 1` (KP vs K endgame)
  - **Expected:** `{a2a3, a2a4}`
  - **Source:** Watkins (pawn advancement is the canonical endgame-stalemate breaker).
  - **What it tests:** does the engine prefer pawn pushes over king shuffles in endgames? Most engines fail this — they shuffle the king.

- **`promotion_at_seventh`** (depth 3)
  - **FEN:** `4k3/P7/8/8/8/8/8/4K3 w - - 0 1` (pawn on 7th)
  - **Expected:** `{a7a8q, a7a8r, a7a8b, a7a8n, a7a8k}` (any promotion)
  - **What it tests:** does the engine promote, or shuffle the king to avoid adding material? A real strategic split — promoting adds material (bad for antichess) but also moves toward Watkins's "force opponent to capture" line.

- **`capture_only_legal_under_forced_rule`** (depth 2)
  - **FEN:** `4k3/8/3p1p2/4P3/8/8/8/4K3 w - - 0 1` (two pawn captures)
  - **Expected:** `{e5d6, e5f6}`
  - Engine must pick a capture; quiet moves are filtered out by the forced-capture rule.

- **`find_pawn_sacrifice_to_force_win`** (depth 4)
  - **FEN:** `8/8/8/8/q7/8/P6P/8 w - - 0 1` (white pawns a2 + h2, black queen a4)
  - **Expected:** `{a2a3}`
  - **What it tests:** white has three legal quiet moves (`a2a3`, `h2h3`, `h2h4`). Only `a2a3` puts the pawn into the queen's capture range, forcing Qxa3 next ply, then white plays h2h3 or h2h4 forcing Qxh3/Qxh4 — white reaches 0 pieces and wins. The h-pawn pushes don't immediately force anything since the queen on a4 can't reach the h-file in one move. Replaces the original `recognize_terminal_win_via_search` (which was just a one-legal-move position and didn't actually test recognition). At depth 4 the engine sees `score_cp ≈ 999996` (≈ MATE_SCORE) when picking `a2a3`.

## Reading the results

Per-engine JSON (`evaluation/results/correctness/<engine>.json`) carries:
```json
{
  "engine_name": "...",
  "tier0_passed": 50, "tier0_total": 50,
  "tier1_passed": 14, "tier1_total": 14,
  "tier2_passed": 5,  "tier2_total": 7,
  "tier0_pass_rate": 1.0, "tier1_pass_rate": 1.0, "tier2_pass_rate": 0.71,
  "results": [{ "test_id": "...", "tier": 0, "passed": true, "detail": "ok", "elapsed_s": 0.0001 }, ...]
}
```

Three columns flow into `experiment_log.csv` via `evaluation.report.update_experiment_log_winrates`: `tier0_pass_rate`, `tier1_pass_rate`, `tier2_pass_rate`. They populate from the per-engine JSON when `update_experiment_log_winrates` runs (after a tournament).

### Current ablation matrix (depth 4)

| Engine | T0 | T1 | T2 |
|---|---|---|---|
| baseline | 50/50 | 14/14 | 3/7 |
| yesarch_yessttrat_noplan | 50/50 | 14/14 | 3/7 |
| arch1-strat1-plan1 | 50/50 | 13/14 | 4/7 |
| noarch_nostrat_yesplan | 50/50 | 13/14 | 3/7 |
| yesarch-nostrat-yesplan | 50/50 | 13/14 | 5/7 |
| yesarch_yesstrat_yesplan_p1 | 50/50 | 13/14 | 4/7 |
| caveman | 50/50 | 12/14 | 4/7 |
| noarch_yesstrat_noplan | 50/50 | 12/14 | 5/7 |
| yesarch_nostrat_noplan | 50/50 | 12/14 | 3/7 |
| **noarch_nostrat_noplan** | 50/50 | **11/14** | 3/7 |

Every engine clears Tier 0 — they all delegate to python-chess's move generator, which agrees with itself by construction. `noarch_nostrat_noplan` (full ablation) bottoms Tier 1 with three rule-class failures: `no_castling_white`, `no_castling_black`, and `inverted_material_white_winning` (uses standard chess material values). Strategy-prompted engines (`noarch_yesstrat_noplan`, `yesarch-nostrat-yesplan`) lead Tier 2 at 5/7. Baseline tops Tier 1 (perfect rule compliance) but trails Tier 2 because it's intentionally a minimal material+mobility engine, not a Watkins-aware one.

### Visualization

`python -m evaluation.correctness_plot` writes `evaluation/results/correctness_matrix.png` — a heatmap with green = pass / red = fail, tier divider lines, and per-engine T0/T1/T2 score boxes. Defaults to showing Tier 1 + Tier 2 rows only (since Tier 0 is uniformly green and dominates the canvas); pass `--include-tier0` for the full 71-row matrix.

## What this suite deliberately does not do

- **No tablebase verification.** Watkins used 4-/5-/6-unit tablebases; generating them is days of work. We hand-author endgame fixtures and accept that some Tier 2 puzzles can't distinguish "engine missed Watkins" from "depth 4 wasn't enough."
- **No proof-number search.** The harness uses alpha-beta `iterative_deepening`. Depth-4 search of an 8-square endgame is not the same as Watkins's cluster-scale PN search.
- **No new engine code.** The suite is purely additive evaluation infrastructure.
- **No changes to `match_loop.py` or the existing tournament pipeline.** Correctness scoring runs orthogonally and writes its own per-engine JSON.
