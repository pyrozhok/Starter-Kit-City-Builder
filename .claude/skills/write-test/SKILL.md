---
name: write-test
description: GUT tests for this project's GDScript. Use when adding or fixing a test, covering a bug, or test-first work on builder, map or UI scripts.
---

# Write test (GUT)

Follow `mattpocock-skills:tdd` for the loop (if it isn't available, tell the user to install the
plugin — see `AGENTS.md`): every new test is seen **red** (bug before the fix, or a
temporarily broken expectation) before it goes green. This skill adds what is specific to GUT and
this project. Terms follow `GLOSSARY.md`.

Run through MCP `godot.run_tests`: `script=` one file, `test_name=` a substring, no args for the suite.
Models to copy: `tests/unit/test_data_map.gd` (resources, save/load) and
`tests/unit/test_builder.gd` (Input-driven node script).

## Conventions

- `tests/unit/test_<script>.gd`, `extends GutTest`, `test_<expected_outcome>()`, typed GDScript.
- Nodes enter the tree through `add_child_autofree()` / `autofree()`.
- Orphans in the report fail the test. `queue_free()` runs at end of frame, after GUT counts: when
  the code under test replaces nodes (e.g. the preview in `update_structure()`), end the test with
  `await get_tree().process_frame`.
- Write files under `user://` and remove them in `after_each`; `res://` stays read-only.
- Reload a saved file with `ResourceLoader.load(path, "", ResourceLoader.CACHE_MODE_IGNORE)` so the
  test reads the disk, not the cache.
- Fill typed exported arrays (`Array[Structure]`) with `.assign([...])`.

## Testing `builder.gd`

`action_*` methods read `Input.is_action_just_pressed(...)`. `Input.action_press("<action>")` makes it
true for the current frame: press, then call the `action_*` method directly in the same frame;
release every pressed action in `after_each`.

Call `builder.set_process(false)` after the builder enters the tree: READY turns `_process` back
on, and `_process` raycasts from a camera the test doesn't have. Give the builder exactly what it
touches: `gridmap`, `selector`, `selector_container`, `cash_display`, `structures` (see
`before_each` in `test_builder.gd`).

The `Audio` autoload runs for real and is silent headless. Reach for `double()` / `stub()` only for a
collaborator whose side effect the test must observe or block.

## Done

- The new test was seen red, then green.
- `godot.run_tests` with no args: `ok: true`, `orphans: 0`, `errors` empty (it lists test files GUT
  skipped on parse errors, and "No tests ran" when a filter matched nothing).
- Report the behaviors covered and the ones left untested (e.g. mouse raycasting in `_process`).

Production code changes only for the fix under test; ask before reshaping it for testability.
