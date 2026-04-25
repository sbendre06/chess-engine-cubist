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
