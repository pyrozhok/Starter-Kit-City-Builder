# write-test eval 003: tasks

Four new tasks for `write-test` at `afc25eb`. They check whether the rules from [001](001.md) carry
over to cases the skill's examples don't name: (e), (f) and (g) for the input rule and red against a
mutant, (h) for `set_process(false)` after entering the tree. Each task goes to a fresh subagent
given only its **prompt**. This file stayed outside the repo until every run had finished.

**Base**: `fork/main` at `afc25eb`, suite 46/46, 0 orphans. Each run starts from an orphan branch
whose only commit is the base tree minus `evals/write-test/`, plus the task's **setup**: no history
and no diff to read an answer from (001 (d) run 1). Runs go one at a time in the main checkout.

Grading: each **grading mutation** is applied on top of the agent's result and its new tests are run.
The **nearest wrong variant** is the one the input rule asks the agent to tell apart; no example in
the skill names it.

## e) A different structure over a tile charges its price

- **Setup**: none.
- **Prompt**: "Building a different structure over a tile that already holds one must charge the new
  structure's price. Cover it with a GUT test. Use the project skill `write-test`. Don't commit; leave
  your changes in the working tree and report what you did."
- **Known answer** (`builder.gd:94-101`): `previous_tile != index` → `map.cash -= structures[index].price`,
  the display updated, the tile rewritten. In the fixture, road-straight costs 25, grass 10.
- **Nearest wrong variant**: charge only on an empty tile (`previous_tile == -1`). A test that builds on
  an empty tile can't tell it apart.
- **Grading mutations**:
  - `e1`: `if previous_tile != index:` → `if previous_tile == -1:`.
  - `e2`: `if previous_tile != index:` → `if false:`.
  - `e3`: `structures[index].price` → `structures[previous_tile].price` (charges the old structure's
    price; tells 25 from 10 only if the two differ).

## f) `rotate` has no test

- **Setup**: none.
- **Prompt**: "`rotate` in `scripts/builder.gd` isn't covered by any test. Add a GUT test for it. Use
  the project skill `write-test`. Don't commit; leave your changes in the working tree and report what
  you did."
- **Known answer** (`builder.gd:114-118`): one press turns the selector +90° around Y
  (`rotate_y(deg_to_rad(90))`) and plays a sound; a build afterwards stores that orientation
  (`get_orthogonal_index_from_basis(selector.basis)`, `builder.gd:95`).
- **Nearest wrong variant**: −90°. A test that only checks the basis changed can't tell it apart, nor
  can one that presses twice (±180° agree).
- **Grading mutations**:
  - `f1`: `deg_to_rad(90)` → `deg_to_rad(-90)`.
  - `f2`: `deg_to_rad(90)` → `deg_to_rad(180)`.
  - `f3`: the `selector.rotate_y(...)` line removed.

## g) Demolish doesn't refund

- **Setup**: none.
- **Prompt**: "Demolish must not refund any cash. Cover it with a GUT test. Use the project skill
  `write-test`. Don't commit; leave your changes in the working tree and report what you did."
- **Known answer** (`builder.gd:105-110`, `GLOSSARY.md`: "no refund"): `map.cash` and the display stay
  as they were.
- **Nearest wrong variant**: refund the demolished structure's price. Only shows on a tile that holds a
  structure (an empty tile skips the demolish).
- **Grading mutations**:
  - `g1`: before `gridmap.set_cell_item(gridmap_position, -1)`, add
    `map.cash += structures[gridmap.get_cell_item(gridmap_position)].price` and `update_cash()`.
  - `g2`: as `g1` but only `map.cash += …` (display not updated): catches a test that reads only the
    label.

## h) `structure_next` from the last structure (the `set_process` rule)

- **Setup**: `before_each` calls `builder.set_process(false)` before the builder enters the tree, as at
  `91a80e9`, and `test_structure_previous_from_first_wraps_to_last_and_switches_preview` is removed
  (it awaits a frame, so it fails on this setup and would give the bug away). Suite on the setup green.
  Checked before the run: a new test that awaits a frame fails with `Cannot call method
  'project_ray_origin' on a null value` (`_process` runs with no camera); the first awaiting test in
  the file, `test_structure_next_switches_preview`, passes.
- **Prompt**: "`structure_next` from the last structure isn't covered by any test. Add a GUT test for
  it. Use the project skill `write-test`. Don't commit; leave your changes in the working tree and
  report what you did."
- **Known answer**: `index = wrap(index + 1, 0, size)` takes the last structure to 0 and rebuilds the
  preview; the test ends with `await get_tree().process_frame` (orphans), which on this setup fails
  until `set_process(false)` moves after `add_child`.
- **Grading**: the result keeps `set_process(false)` after the builder enters the tree, and the suite
  is green. Mutations: `h1`: `index + 1` → `index` (no wrap); `h2`: the `update_structure()` call
  removed.

## What is measured

As in 001: red → green (on a mutant), catches the mutations, orphans, edits by a human, time; plus,
per task, whether the agent picked inputs that tell the behavior from its nearest wrong variant (e, f,
g) or fixed the fixture (h) without being told.
