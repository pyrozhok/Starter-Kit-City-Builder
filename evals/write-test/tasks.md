# write-test eval 001: tasks with a known answer

Four tasks for the `write-test` skill (`.claude/skills/write-test/SKILL.md`), each given to a fresh
subagent session with only the **prompt** below: no hints from the session that set it up. This file
stayed outside the repo until every run had finished, so no agent could read the answers.

Each run starts from the same clean tree, **base** = `fork/main` at `91a80e9` (GUT 43/43, 0
orphans), plus the **setup** of its task. Runs go one after another in the main checkout, because
`godot.run_tests` runs the project the MCP server's own file sits in, not a worktree.

Grading is done by the session that set the tasks, not the agent: each **grading mutation** is
applied on top of the agent's result and the agent's new tests are run. A test that stays green on
the mutation does not catch the behavior it was written for.

## a) `structure_previous` has no test

- **Setup**: none.
- **Prompt**: "`structure_previous` in `scripts/builder.gd` isn't covered by any test. Add a GUT test
  for it. Use the project skill `write-test`. Don't commit; leave your changes in the working tree and
  report what you did."
- **Known answer** (`builder.gd:129-135`): pressing `structure_previous` sets
  `index = wrap(index - 1, 0, structures.size())` (from 0 it goes to the last structure), plays a sound
  and rebuilds the preview once. With the two structures `test_builder.gd` uses, previous and next
  both take 0 to 1, so a test with two structures, starting from 0, can't tell them apart.
- **Grading mutations**:
  - `a1`: `index - 1` → `index + 1` (previous behaves like next).
  - `a2`: the `structure_previous` block removed (the action does nothing).

## b) Building the same structure again on a tile doesn't charge

- **Setup**: none.
- **Prompt**: "Building the same structure again on a tile that already holds it must not charge cash.
  Cover this with a GUT test. Use the project skill `write-test`. Don't commit; leave your changes in
  the working tree and report what you did."
- **Known answer** (`builder.gd:94-99`): `previous_tile != index` gates the charge, the cash display
  and the sound; the tile is still rewritten (orientation can change). Building a *different* structure
  over a tile does charge.
- **Grading mutations**:
  - `b1`: `if previous_tile != index:` → `if true:` (every build charges).
  - `b2`: `if previous_tile != index:` → `if false:` (no build charges). Not the claimed behavior: a
    test that catches it also checks that the first build charged, so it can't pass by charging
    nothing.

## c) Demolish returns the tile to -1

- **Setup**: none.
- **Prompt**: "Demolish must return the tile to -1 (empty). Cover it with a GUT test. Use the project
  skill `write-test`. Don't commit; leave your changes in the working tree and report what you did."
- **Known answer** (`builder.gd:105-110`): with `demolish` just pressed and the pointer not over UI, a
  tile that isn't -1 is set to -1 (`GridMap.INVALID_CELL_ITEM`). No refund (`GLOSSARY.md`).
- **Grading mutations**:
  - `c1`: the `gridmap.set_cell_item(gridmap_position, -1)` line removed.
  - `c2`: `-1` → `1` in that line (the tile gets another structure instead of being cleared).

## d) The `pointer_over_ui()` check removed

- **Setup**: in `scripts/builder.gd`, `and not pointer_over_ui()` removed from both `action_build` and
  `action_demolish` (`pointer_over_ui()` itself stays, now unused). The two tests that already catch it
  (`test_build_is_ignored_while_pointer_is_over_ui`, `test_demolish_is_ignored_while_pointer_is_over_ui`)
  and their helper `_hover_new_button` removed from `tests/unit/test_builder.gd`, together with the
  `SubViewport` the builder is added to: otherwise the answer is already in the repo. The suite is green
  on this setup (41/41).
- **Prompt**: "Bug: clicking on the UI also builds or demolishes on the map under the pointer (e.g.
  clicking a menu button places a road behind it). Write a test that catches it, then fix it. Use the
  project skill `write-test`. Don't commit; leave your changes in the working tree and report what you
  did."
- **Known answer**: the revert of the setup's change to `builder.gd`: `and not pointer_over_ui()` back
  in both actions.
- **Grading mutations**: the setup itself (the agent's tests must be red on it), and each half alone:
  - `d1`: only `action_build`'s check removed.
  - `d2`: only `action_demolish`'s check removed.

## What is measured

| Column | How |
|---|---|
| red → green | red on the setup (d) or on a grading mutation (a–c), green on the code with the behavior; the agent's own report of what it saw red is noted too |
| catches the mutation | each grading mutation applied on top of the agent's result: its new tests red |
| orphans | `godot.run_tests` with no args on the agent's result: `orphans: 0`, `ok: true` |
| edits by a human | changes to the agent's output needed before it can be committed |
| time | the subagent's wall-clock time |
