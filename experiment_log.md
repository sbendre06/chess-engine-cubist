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

## Session: arch0

**Date:** 2026-04-25
**Operator:** claude-sonnet-4-6
**Goal:** Implement arch0 Antichess engine with burden-based evaluation, attacked-piece bonus, and mobility penalty

### Token usage
- Input tokens: TBD (run `/cost` at session end)
- Output tokens: TBD

### Wall-clock time
- Total elapsed: TBD

### Human interventions
- Count: 0
- Notes: No interventions required

### Bugs and issues fixed
1. System python3 (3.9) incompatible with `dataclass(slots=True)` — used `uv run --python 3.11` for testing
2. UCI heredoc test cuts off before `bestmove` (stdin EOF kills process) — verified via direct Python import instead

### Outcome
- Implemented `engines/arch0.py` with three contract functions
- Evaluation: inverted piece burden (pawn=500, queen=100), attacked-piece bonus, mobility penalty
- Move ordering: captures first, prefer capturing low-burden pieces, promotion priority, attack-zone moves
- Searches to depth 4 correctly; `bestmove g2g3` from start position at depth 4
- Created `engines/arch0.tokens.csv` (update with actual token counts at session end)
