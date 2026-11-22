# write-test eval 004: with vs without the skill

- **Tasks**: (a)–(d) from [`tasks.md`](tasks.md), (e)–(h) from [`tasks-003.md`](tasks-003.md), same prompts.
  Baseline prompts drop the sentence "Use the project skill `write-test`."
- **Date**: 2026-11-22
- **Skill version**: `.claude/skills/write-test/SKILL.md` at `1ee923f` (after #19).
- **Code under test**: `scripts/builder.gd` at `97ad620`.
- **Setup** ([`004/setup_run.py`](004/setup_run.py)): per run, a repo whose only commit is `97ad620`'s
  tree minus `evals/`, `README.md` (it names the skill's rules) and the task's answer: the tests on
  `main` that cover it, and for (d) and (h) the setups from the task files. Baseline also minus
  `.claude/skills/write-test/`. Both arms keep the plugin's `tdd` and the other project skills.
  Suite on each setup green, 0 orphans.
- **Agents** ([`004/drive.sh`](004/drive.sh)): one fresh headless `claude -p` session per run (Opus 5.5),
  given only the prompt, one at a time, in its own run repo with its own `godot` MCP server. Not
  subagents: a subagent inherits the session's skill list, so it would still list `write-test`. Checked
  before the runs: the baseline session doesn't list `write-test`, the skill session does, both have
  `mcp__godot__run_tests`. Allowed without asking: edits, `mcp__godot__*`, and Bash `godot`, `uv`,
  `ls`, `grep`, `git status`, `git diff`.
- **Skill arm**: all 8 tasks rerun in this harness, instead of reusing 003 for (e)–(h) as #22 planned:
  the skill changed after 003 (#19), and the harness is different. 003's times for (e)–(h) (41 s,
  58 s, 37 s, 1 min 4 s) are close to this run's.
- **Graded by** ([`004/grade.py`](004/grade.py)): the session that set the runs. Each grading mutation is
  applied on top of the agent's result; it is caught when at least one test the agent added fails on
  it. The grades are proposals the user approves (column *Approved*), 2026-11-22: all as proposed.

## Result

| Task | Arm | Red → green | Catches the mutations | Nearest wrong variant | Orphans | Edits by a human | Time | Approved |
|---|---|---|---|---|---|---|---|---|
| a) `structure_previous` | baseline | ✅ red on `index + 1` | ✅ `a1`, `a2` | ✅ three structures | 0 | 0 ¹ | 1 min 7 s | ✅ |
| | skill | ✅ red on `index + 1` | ✅ `a1`, `a2` | ✅ three structures | 0 | 0 | 33 s | ✅ |
| b) same structure again doesn't charge | baseline | ✅ red with the check removed | ⚠ `b1`; `b2` survives | — | 0 | 0 | 46 s | ✅ |
| | skill | ✅ red on `if true` | ⚠ `b1`; `b2` survives | — | 0 | 0 | 34 s | ✅ |
| c) demolish empties the tile | baseline | ✅ red on writing `0` | ✅ `c1`, `c2` | — | 0 | 0 | 42 s | ✅ |
| | skill | ✅ red on writing `index` | ✅ `c1`, `c2` | — | 0 | 0 | 40 s | ✅ |
| d) `pointer_over_ui()` check removed | baseline | ✅ red on the setup | ✅ `d0`, `d1`, `d2` | — | 0 | 0 | 1 min 12 s | ✅ |
| | skill | ✅ red on the setup | ✅ `d0`, `d1`, `d2` | — | 0 | 0 | 1 min 4 s | ✅ |
| e) different structure over a tile charges | baseline | ✅ red on `e1` | ✅ `e1`, `e2`, `e3` | ✅ | 0 | 0 | 40 s | ✅ |
| | skill | ✅ red on `e3` | ✅ `e1`, `e2`, `e3` | ✅ | 0 | 0 | 39 s | ✅ |
| f) `rotate` | baseline | ✅ red on −90° | ✅ `f1`, `f2`, `f3` | ✅ | 0 | 0 | 39 s | ✅ |
| | skill | ✅ red on −90° (3 tests, each red on its own mutant) | ✅ `f1`, `f2`, `f3` | ✅ | 0 | 0 | 56 s | ✅ |
| g) demolish doesn't refund | baseline | ✅ red on a +1 refund | ✅ `g1`, `g2` | ✅ priced tile | 0 | 0 | 30 s | ✅ |
| | skill | ✅ red on a refund | ✅ `g1`, `g2` | ✅ priced tile | 0 | 0 | 36 s | ✅ |
| h) `structure_next` from the last | baseline | ❌ never saw red ² | ⚠ `h1`, `h2`; `h3` survives | ❌ two structures | 0 | 0 | 55 s | ✅ |
| | skill | ✅ red on a clamp | ✅ `h1`, `h2`, `h3` | ✅ three structures | 0 | 0 | 1 min | ✅ |

Mutations caught: baseline 18/20, skill 19/20. Every result: suite green, `orphans: 0`, `errors` empty.
Total time: baseline 6 min 30 s, skill 6 min 2 s.

¹ A one-character whitespace change left in `builder.gd`: the agent couldn't revert its mutant with
`git restore`, which the harness didn't allow. A harness artifact, not counted.
² Its one try at a mutant was a `sed` command, which the harness denied; it didn't try the Edit tool.

## What the skill adds

On (a)–(g) nothing measurable: without the skill, Opus 5.5 picked inputs that tell the behavior from
its nearest wrong variant and saw its test red on a mutant, unprompted. The three general rules from
001 are what the model does anyway.

On (h) it adds what a model can't derive from the code:

- **`set_process(false)` after entering the tree.** The baseline hit the `_process` error, understood
  it ("the builder turns processing back on when it enters the tree"), but worked around it with
  `preview.free()` instead of an `await`, leaving the fixture as it was. The skill arm moved the call
  and cited the skill.
- **Inputs.** The baseline kept the fixture's two structures, where `index - 1` from the last also
  gives 0 (`h3` survives). The skill arm added a third.

So on this model the skill's value is its project knowledge, not its method: [#28](https://github.com/pyrozhok/Starter-Kit-City-Builder/issues/28).

## Findings

### b2 survives in both arms

`b2` (no build charges) survives because both tests check only that the repeat build leaves cash
unchanged, not that the first build charged. 001 named this in the task file; no rule in the skill
covers it: [#29](https://github.com/pyrozhok/Starter-Kit-City-Builder/issues/29).

### The task set barely separates the arms

One clear difference in 8 tasks, one run per arm per task, all on `builder.gd`. Harder tasks on
project traps and other scripts, repeated runs and a smaller model would say more:
[#30](https://github.com/pyrozhok/Starter-Kit-City-Builder/issues/30), [#26](https://github.com/pyrozhok/Starter-Kit-City-Builder/issues/26).

## Changes to the tasks

- **(h) setup**: on `97ad620`, `test_structure_next_switches_preview` and
  `test_rotate_is_ignored_without_press` also fail on the setup (at `afc25eb` they passed), and would
  give the bug away; removed too. Suite on the setup 47/47.
- **`h3`** (`index + 1` → `index - 1` in `structure_next`): new grading mutation, the nearest wrong
  variant `tasks-003.md` names for (h).

## Left open

- The grader's first pass read the wrong key of `run_tests`' result and marked every mutation
  survived; caught by its implausibility and regraded. The grader has no test.
- One `godot --import` of a fresh run repo crashed (SIGABRT from Godot's crash handler, no symbols);
  rebuilt, and the retry passed.
- The agents' tests aren't committed: (a)–(h) are already covered on `main`.
