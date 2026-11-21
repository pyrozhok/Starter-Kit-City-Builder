# write-pytest eval 001: pytest suite for `godot_mcp.py` (issue #2)

- **Target**: issue #2, sections 1–7 of its test plan and its red phase.
- **Date**: 2026-11-21
- **Skill version**: `.claude/skills/write-pytest/SKILL.md` at `1cea235` for the run; `94ffe62` adds the run's lessons, `eea0993` the roast's.
- **Code under test**: `tools/mcp/godot_mcp.py` at `91052d8`; one fix during the roast (`81c1b65`).
- **Graded by**: not graded yet. The numbers below are measured, but the agent that wrote the tests also ran the measurements.

Two passes: the **run** wrote the suite (`4dfc4a6`); a **roast** of that suite, asked for by the user, found it weaker than reported and reworked it (`30229be`–`ba54aff`).

## Result

| Check | Run (`4dfc4a6`) | After the roast (`ba54aff`) |
|---|---|---|
| Tests | 47, 2.0 s | 63, 3.4 s |
| Godot in the tests | a shell-script fake that ignored its arguments, plus a stubbed `_godot` | `FakeGodot`, an executable that reads `--path` and `-gjunit_xml_file` like Godot; no stubs |
| Data | real captures, plus hand-written JUnit and `_godot` results | 5 real captures (`tools/mcp/tests/fixtures/`); one defensive case, labelled |
| Generated mutants killed ([`mutants.py`](../../tools/mcp/tests/mutants.py)) | 299/453; 299/352 outside `screenshot` (85%) | 337/453; 337/352 outside `screenshot` (96%) |
| Over MCP (client session) | none | 3 tests, one found a bug |
| Bugs found in `godot_mcp.py` | 0 | 1: a refused path reached the agent with no reason (`81c1b65`) |
| CI | none | `.github/workflows/tools.yml`, checked in a clean clone with an empty HOME, not yet run on GitHub |

Both: passes with `GODOT_BIN=/nonexistent`; Godot side unchanged (`--import` ok, `check_scripts.gd` 17/17, GUT 43/43, 0 orphans, no new `.gd`, `.uid` or `.import` files).

## Red phase

`GODOT_MCP_PATH` = `git show <commit>:tools/mcp/godot_mcp.py`. Same result for the run's suite and the roast's.

| Commit | Tests | Expected (issue) | Result |
|---|---|---|---|
| `925a7ed^` | `files_changed_by_build` (9) | the restores-dirty-to-head and deletes-untracked rows fail | those 2 fail, 7 pass ✅ |
| `925a7ed` | same | pass | 9 pass ✅ |
| `5da9c8c^` | GUT missing, no JUnit + Godot error, export without presets | fail | 3 fail ✅ |
| `5da9c8c` | same | pass | 3 pass ✅ |
| `ad102ed^`, `ad102ed` | missing binary, timeout | pass on both (the refactor kept behavior) | 2 pass on both ✅ |
| `81c1b65^` | refused path over MCP | — (found in the roast) | fails ✅; passes on `81c1b65` |

## Surviving mutants, outside `screenshot`

| Mutants | Why they survive |
|---|---|
| Timeouts n+1 (`30`, `600`, `300`, `1200`, `900`), 5 | equivalent: a test can't tell 600 s from 601 s |
| `"<deleted>"` marker, `errors="replace"` (2), the prefix of "Path escapes project" | equivalent for the inputs the tool gets; tests match the reason, not the prefix |
| `_git_snapshot`: `if returncode != 0` / `return {}` removed | equivalent: a failing git prints nothing on stdout, so the snapshot is empty either way |
| `_parse_tscn`: `split("=", 1)` → `split("=", 2)` | equivalent: `[1]` is the same unless the value has two `=` |
| `_parse_tscn`: `current = None` on a new section removed | reachable only with a `[sub_resource]` after a node; Godot writes sub-resources before nodes |
| `_godot`: tail length n+1 on the timeout path | not tested; the finished-run path is |
| `run_tests`: `"USER ERROR"` in the script-error prefixes | no capture shows Godot 4.7 printing `USER ERROR` (`push_error` prints `ERROR`); possibly dead, unverified |

`screenshot`: 0/101, untested (needs a windowed Godot and a display).

## Deviations from the issue

- **Run command**: `pytest --import-mode=importlib tools` instead of `pytest tools/mcp/tests`, so future suites under `tools/` run with it. The command is in `AGENTS.md` and CI; the issue body still has the old one (editing the issue was blocked by the session's permission classifier).
- **No stubbed `_godot`**: the issue's "Stubbed `_godot`" seam was replaced by `FakeGodot` in the roast (mistake 6).
- **Added**: section 8 (the tool contract the skills rely on), section 9 (over MCP), CI.

## Mistakes and the rules they became

| # | What happened | Caught by | Rule |
|---|---|---|---|
| 1 | The Done criterion only knew "red on `<sha>^`", which turned 5 of 47 tests red | reading the criterion against the plan | `94ffe62`: red for behavior no commit broke |
| 2 | Helpers in `conftest.py` imported from the test file fail under `--import-mode=importlib` | before the first run | `94ffe62`: fixtures in `conftest.py`, helpers in the test file |
| 3 | Fixture lines selected by `.endswith(...)`; real lines end with an ANSI reset code | first run: the test's own guard assert | `94ffe62`: select lines by their text |
| 4 | Git setup passed only `-c user.name/email`; global config (signing, hooks) could still apply | review, not observed | `94ffe62`: `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_NOSYSTEM`, `GIT_CEILING_DIRECTORIES` |
| 5 | Older copies of `_godot` take `(args, timeout)` | reading the red-phase commits | `94ffe62`; moot after the roast (no stubs) |
| 6 | **Reported "26/26 mutations killed".** The 26 were picked by the test author after writing the tests. Generated mutants: 299/453 | roast | `eea0993`: generated mutants, `mutants.py` in Done |
| 7 | No command line was checked: the fake ignored argv, the stub wrote JUnit whatever the flags. A broken `-gjunit_xml_file`, `--path` or `--headless` passed | roast, generated mutants | `eea0993`: the seam is the process; pin argv to commands proven on real Godot |
| 8 | `test_gut_missing` passed with the GUT check deleted (it asserted only keys and `ok`) | roast, generated mutants | `30229be`: the exact result, and Godot never started |
| 9 | Hand-written data where Godot's behavior was unknown (an empty run's JUnit, an ERROR inside a passing test) | roast | `eea0993`: capture first. The capture showed GUT fails such a test itself |
| 10 | The tool-parameter test was a schema snapshot: an optional parameter turned it red | roast | `eea0993`: contract as a subset |
| 11 | All 47 tests written in one pass, red seen afterwards: the horizontal slicing `tdd` warns against | roast | none: acceptable for characterising existing code, recorded here |
| 12 | The mutation runs left ~240k temp files and exhausted `/tmp`'s inodes | `No space left on device` | `fc1c5d1`: `mutants.py` removes each run's temp dir |

## Left untested

- `screenshot`: needs a windowed Godot and a display.
- A real Godot run of `build` / `run_tests`: the command lines are pinned to runs made by hand while writing the suite; nothing re-runs them.
- `tools/design/figcraft.py`: no suite yet.
