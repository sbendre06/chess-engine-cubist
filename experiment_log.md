# experiment_log.md

A running log of Claude Code sessions on this repo. One section per session.
Per-engine cost rows live in `experiment_log.csv` (built up by
`log_experiment.py`); this Markdown file holds the qualitative session notes
the CSV doesn't capture (bugs hit, what was learned).

---

## Session: ablation harness build

**Date:** 2026-04-24
**Operator:** Claude Code (Opus 4.7, 1M context) + austinsenna
**Goal:** Restructure the repo into a frozen harness + per-agent
`engines/<name>.py` + evaluation tournament so the prompt-ablation study can
proceed in parallel.

### Token usage

I do not have direct visibility into my own session token totals from inside
the session. Run Claude Code's `/cost` slash command at the END of the
session and copy the numbers below.

- **Input tokens:** _<fill from `/cost`>_
- **Output tokens:** _<fill from `/cost`>_
- **Total:** _<input + output>_

To record this session in the CSV with concrete numbers:

```bash
python log_experiment.py \
    --name harness_build \
    --tokens-in <from /cost> \
    --tokens-out <from /cost> \
    --minutes <wall-clock> \
    --interventions 13
```

`engine_winrate` is left blank by `log_experiment.py` and is populated
automatically the next time `python -m evaluation.tournament` runs against
the named engine.

### Wall-clock time

Approximate: this session ran across multiple back-and-forth turns covering
brainstorming → plan → implementation → ablation-purity cleanup → push. The
operator's clock is the source of truth; check Claude Code's session-start
timestamp.

- **Estimated total elapsed:** _~90–120 minutes_ (fill exact value)

### Human interventions

Counted as: each distinct user message submitted to the session (whether
free-form text or an answer to AskUserQuestion). Slash commands like
`/usage` are not counted unless they carried additional content.

**Count: 13.**

Rough timeline:

1. Initial restructuring request (referencing `context.txt`).
2. "What is gonna be the foundation api if its 4?"
3. "What is terminal call for? If its useful and varies by engines we can use it"
4. "okay lets do that then" (Core 3 confirmed)
5. AskUserQuestion batch: variant + layout + logging answers.
6. "A" — flat layout reconciliation.
7. "Hi can you continue" — resumed after pause.
8. Caught the baseline-leak bug: branch-template should not carry baseline.
9. Caught the strategy-contamination bug: docstrings leaked Strategy
   content into the agent surface.
10. Approved deletion list for branch-template.
11. "okay commit and push,"
12. Logging task request: build `experiment_log.md` + `log_experiment.py`,
    plus cleanup gitignored-but-tracked files on main.
13. `/usage` + "continue" after a brief interrupt.

### Bugs and issues fixed

#### Code / environment

1. **System Python was 3.9** but the harness uses `@dataclass(slots=True)`
   (3.10+). Fixed by creating a project-local `.venv` via uv with Python
   3.13, then installing python-chess + pytest there.
2. **First UCI smoke test cut off** because the test pipeline sent `quit`
   immediately after `go`, interrupting the search. Fixed the test driver
   (`/tmp/uci_test.py`) to wait for `bestmove` before sending quit. Not a
   harness bug — actual UCI behavior is correct.
3. **`git rm -rf` over-broad** when stripping branch-template: included
   unauthorized paths and was denied by the permission system. Recovered
   by narrowing scope to user-confirmed deletions and splitting into two
   `git rm` calls.
4. **Stale tracked `__pycache__/main.cpython-313.pyc`** survived on
   branch-template even after the strip. Removed in a follow-up commit.
5. **34 `__pycache__/*.pyc` files were tracked across the repo** despite
   `.gitignore` listing `__pycache__/`. Untracked with
   `git rm -r --cached`.

#### Ablation-purity contamination (caught by operator)

6. **`engines/_template.py` docstring leaked Strategy** ("material and
   mobility signs are INVERTED") to all agents, defeating the
   "no_strategy" branch. Fixed: stripped to signatures only, bodies
   raise `NotImplementedError`.
7. **AGENTS.md "rules crib" leaked Strategy** via the same "inverted
   signs" bullet. Fixed: trimmed to the three actual antichess rules
   (forced captures, stalemate-wins, bare-pieces-wins).
8. **`harness/engine.py` carried unused `PIECE_VALUES` constant** —
   dead code that would have leaked classical piece values to anyone
   peeking at the harness. Fixed: removed.
9. **Initial design had baseline on every branch** — agents would have
   seen the reference implementation. Fixed: introduced the three-branch
   model (`main` / `branch-template` / `agent/<name>`) before
   implementing.
10. **`branch-template` initially carried antiengine/, classicalengine/,
    benchmarks/, tests/, tools/, tuning/, docs/, context.txt,
    parsed_slides.txt, DESIGN.md, ROADMAP.md** — all study-design or
    prior-art that would taint the experiment. Fixed: deleted in one
    commit on branch-template.

### Outcome

- `main` (origin/main, `c063231`): full state including `engines/baseline.py`.
- `branch-template` (origin/branch-template, `1d9eaa5`): minimal starter
  kit. Agents branch from here.
- `log_experiment.py` + `experiment_log.csv` (auto-created on first run)
  in place for per-session cost logging going forward.
- `engines/<name>.tokens.csv` schema documented in `AGENTS.md` for
  per-engine build-time cost.

### Lessons for future sessions

- Auto mode is fine for execution but the operator should still gate
  destructive cleanups (deleting whole directories, force-pushing). The
  permission system catching the over-broad `git rm` was the right call.
- Ablation studies care about leakage in places you wouldn't normally
  audit: docstrings, dead code in shared infrastructure, README files.
  Treat the entire branch-template as the agent's prompt and review
  every line.
- Manual `/cost` entry for tokens is the right starting point; only
  invest in transcript parsing if cost-of-friction becomes real.

---

## Session: noarch_nostrat_yesplan

**Date:** 2026-04-25
**Operator:** Claude Sonnet 4.6
**Goal:** Build an Antichess engine with plan-guided design but no architecture docs and no strategy hints

### Token usage
- Input tokens: 20438
- Output tokens: 3105

### Wall-clock time
- Total elapsed: 43 minutes

### Human interventions
- Count: 1
- Notes: User provided Antichess rules inline; no other corrections needed

### Bugs and issues fixed
1. venv not present on branch — recreated with `uv venv --python 3.13` and installed python-chess
2. Initial test showed only depth-1 info line — root cause was `quit` arriving before search thread completed; confirmed normal with `go movetime 3000` test (depths 1-4 all completed)

### Outcome
Landed `engines/noarch_nostrat_yesplan.py` with:
- `get_pseudo_legal_moves`: delegates to `board.legal_moves` (mandatory captures enforced)
- `evaluate_board`: -own_material + ½ bonus per piece attacked by opponent
- `order_moves`: captures-that-expose-our-piece first, then other captures, then exposure non-captures
Engine searches depth 4 in ~1.2s from starting position (~10k nodes). Next: run tournament vs baseline.
