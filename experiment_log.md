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

## Session: yesarch-nostrat-noplan

**Date:** 2026-04-25
**Operator:** Claude (claude-sonnet-4-6)
**Goal:** Build Antichess engine with good move-ordering architecture but no strategic evaluation or pre-computed plans.

### Token usage
- Input tokens: ~80,000
- Output tokens: ~2,000

### Wall-clock time
- Total elapsed: ~15 minutes

### Human interventions
- Count: 1
- Notes: Initial prompt only; engine was written and tested autonomously.

### Bugs and issues fixed
1. Module name: branch uses hyphens (`yesarch-nostrat-noplan`) but Python modules require underscores — used `yesarch_nostrat_noplan.py`.
2. UCI race: quick `echo | python main.py` sends `quit` before depth-4 search finishes; confirmed full search with `sleep` between `go` and `quit`.

### Outcome
Engine `yesarch_nostrat_noplan` is functional. Three functions implemented:
- `get_pseudo_legal_moves`: returns all pseudo-legal moves (harness filters to legal).
- `evaluate_board`: inverted material (opp_cost − my_cost) + mobility penalty (−10 per legal move) + exposure bonus (+4× piece_cost for each of our pieces attacked by opponent).
- `order_moves`: captures sorted by attacker value + chain-recapture bonus; non-captures sorted by whether destination is attacked (exposure-first).
No opening book, no endgame tables, no positional strategy — pure architecture/search efficiency.

After filling in this section, also run:

```bash
python log_experiment.py \
    --name <your-engine-name> \
    --tokens-in <N> --tokens-out <N> \
    --minutes <N> --interventions <N>
```

The `engine_winrate` column in `experiment_log.csv` is populated
automatically the next time `python -m evaluation.tournament` runs.
