# write-pytest eval 001: pytest suite for `godot_mcp.py` (issue #2), first run

- **Target**: issue #2, sections 1–7 of its test plan and its red phase.
- **Date**: 2026-11-21
- **Skill version**: `.claude/skills/write-pytest/SKILL.md` at `1cea235` for the run; `94ffe62` adds this run's lessons.
- **Code under test**: `tools/mcp/godot_mcp.py` at `91052d8` (unchanged by the run).
- **Graded by**: not graded yet.

## Result

| Check | Result |
|---|---|
| Suite | 47 tests in `tools/mcp/tests/test_godot_mcp.py` (`4dfc4a6`), 2.0 s |
| No Godot | passes with `GODOT_BIN=/nonexistent`; every test runs a fake Godot, a stubbed `_godot`, or no Godot at all |
| Red phase from the issue | 3/3 commits as the issue predicts (table below) |
| Behavior no commit broke | 26/26 mutations turn at least one test red ([`001/mutate.py`](001/mutate.py)) |
| Godot side | `--import` ok, `check_scripts.gd` 17/17, GUT 43/43 with 0 orphans; no new `.gd`, `.uid` or `.import` files |
| Bugs found in `godot_mcp.py` | 0 |

## Red phase

`GODOT_MCP_PATH` = `git show <commit>:tools/mcp/godot_mcp.py`.

| Commit | Tests | Expected (issue) | Result |
|---|---|---|---|
| `925a7ed^` | `files_changed_by_build` (9) | the restores-dirty-to-head and deletes-untracked rows fail | those 2 fail, 7 pass ✅ |
| `925a7ed` | same | pass | 9 pass ✅ |
| `5da9c8c^` | GUT missing, no JUnit + Godot error, export without presets | fail | 3 fail ✅ |
| `5da9c8c` | same | pass | 3 pass ✅ |
| `ad102ed^`, `ad102ed` | missing binary, timeout | pass on both (the refactor kept behavior) | 2 pass on both ✅ |

## Deviations from the issue

- **Run command**: `pytest --import-mode=importlib tools` instead of `pytest tools/mcp/tests`, so future suites under `tools/` (e.g. `figcraft.py`) run with it. The import mode keeps two `conftest.py` files from clashing. The command is in `AGENTS.md`; the issue body still has the old one.
- **Section 8, added**: the names and parameters of the five tools, which the skills call. Renaming a parameter turns it red (mutation `tool-param`).
- **Orphan fixture**: eval 003 records the conclusion of its probe, not its output, so the fixture was captured again from Godot 4.7.2 / GUT 9.7.1 (`tools/mcp/tests/fixtures/README.md`).

## Mistakes and the rules they became

| # | What happened | Caught by | Rule (`94ffe62`) |
|---|---|---|---|
| 1 | The Done criterion only knew "red on `<sha>^`". That covers the 5 tests for bugs fixed in history; the other 42 had no way to be seen red | reading the criterion against the plan | Red for behavior no commit broke: a mutated copy through `GODOT_MCP_PATH`; a mutation that stays green is a missing test |
| 2 | Helpers in `conftest.py` imported from the test file: under `--import-mode=importlib` that import fails | before the first run | Fixtures in `conftest.py`, plain helpers in the test file |
| 3 | The orphan test selected fixture lines by `.endswith("1 orphans")`; real lines end with an ANSI reset code, so nothing matched | first run: 1 red, the test's own guard assert | ANSI codes stay in fixtures; select lines by their text |
| 4 | The skill's git setup only passed `-c user.name/email`; the user's global config (commit signing, hooks) could still reach the fixture's commit | review of the fixture, not observed | `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1`, `GIT_CEILING_DIRECTORIES` |
| 5 | Older copies of `_godot` take `(args, timeout)`, with no `headless` | reading the red-phase commits | Stubs keep `headless` optional |

## Left untested

- `screenshot`: needs a windowed Godot and a display; only its parameters are pinned (section 8).
- A real Godot run of `build` / `run_tests`: covered by `godot.*` calls in the skills, not by pytest.
- `tools/design/figcraft.py`: no suite yet; the skill and the run command already cover `tools/`.
