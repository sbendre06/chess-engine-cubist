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

## Session: yesarch-yesstrat-yesplan

**Date:** 2026-04-25
**Operator:** Claude (caveman session)
**Goal:** Build full-ablation Antichess engine: bitboard architecture + strategic evaluation + Watkins opening plan.

### Token usage
- Input tokens: 10842
- Output tokens: 3216

### Wall-clock time
- Total elapsed: ~15 minutes

### Human interventions
- Count: 1
- Notes: Single prompt, fully autonomous build.

### Bugs and issues fixed
1. No bugs — first test passed (e2e3 from book, a2a4 vs Liardet).

### Outcome
Engine `yesarch_yesstrat_yesplan.py` written and verified. Three functions implemented:
- `get_pseudo_legal_moves`: pseudo-legal move gen with captures partitioned first.
- `evaluate_board`: bitboard-based score using piece badness, capture liability, piece count.
- `order_moves`: Watkins opening book (e3 + 13 second-move responses), rook-preferred promotions, capture/quiet ordering.
Next: run tournament to measure win-rate vs other ablation variants.
