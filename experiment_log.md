# experiment_log.md

A running log of Claude Code sessions on this repo. One section per session.
Per-engine cost rows live in `experiment_log.csv` (built up by
`log_experiment.py`); this Markdown file holds the qualitative session notes
the CSV doesn't capture (bugs hit, what was learned).

## How to add a session entry

At the end of your session, append a section using this template:

```markdown
## Session: <short name>

**Date:** YYYY-MM-DD
**Operator:** <your name>
**Goal:** <one-line summary of what this session was for>

### Token usage
- Input tokens: <from `/cost`>
- Output tokens: <from `/cost`>

### Wall-clock time
- Total elapsed: <minutes>

### Human interventions
- Count: <number>
- Notes: <any patterns you noticed>

### Bugs and issues fixed
1. <bug 1>
2. <bug 2>
...

### Outcome
<what landed, what's next>
```

After filling in this section, also run:

```bash
python log_experiment.py \
    --name <your-engine-name> \
    --tokens-in <N> --tokens-out <N> \
    --minutes <N> --interventions <N>
```

The `engine_winrate` column in `experiment_log.csv` is populated
automatically the next time `python -m evaluation.tournament` runs.

## Session: noarch_yesstrat_noplan

**Date:** 2026-04-25
**Operator:** Claude Sonnet 4.6 (noarch_yesstrat_noplan)
**Goal:** Build an Antichess engine with Watkins-informed strategy but no custom architecture and no explicit planning phase.

### Token usage
- Input tokens: ~8500
- Output tokens: ~1800

### Wall-clock time
- Total elapsed: 15 minutes

### Human interventions
- Count: 0
- Notes: No human interventions required

### Bugs and issues fixed
1. `board.occupied_co[color]` returns a bitboard int, not a sized container — fixed by using `bin(...).count('1')` for piece counts.
2. UCI test showed only depth 1 completed — root cause was `quit` command racing the search thread; verified correct behavior via direct Python call (depth 4 completes in ~6s).

### Outcome
Delivered `engines/noarch_yesstrat_noplan.py` with three required callables:
- `get_pseudo_legal_moves`: returns all pseudo-legal moves (harness filters to legal).
- `evaluate_board`: scores position by own burden (inverted piece values per Watkins), mobility, pawn advancement, and stalemate proximity.
- `order_moves`: prioritizes captures that sacrifice high-burden own pieces, then pawn advances, then exposure moves.

Engine reaches depth 4 from startpos in ~6s. Next steps: tournament evaluation.
