# write-pytest eval 001: pytest suite for `godot_mcp.py` (issue #2)

- **Target**: issue #2, sections 1–7 of its test plan and its red phase.
- **Date**: 2026-11-21
- **Skill version**: `.claude/skills/write-pytest/SKILL.md` at `1cea235` for the run; `94ffe62` adds the run's lessons, `eea0993` the roast's, `e6cf424` the third pass's.
- **Code under test**: `tools/mcp/godot_mcp.py` at `91052d8`; three fixes on the way (`81c1b65`, `89d486f`, `aeb1e0e`).
- **Graded by**: a separate Claude session (Opus 5.5), 2026-11-21, not the agent that wrote the tests. Numbers reproduced: 432/458 with the same 26 survivors; 77 tests, all passing with Godot 4.7.2 and 76 + 1 skipped with `GODOT_BIN=/nonexistent`; every bug test red on `<sha>^`, green on `<sha>`.

Three passes:
1. The **run** wrote the suite (`4dfc4a6`).
2. A **roast** of that suite, asked for by the user, found it weaker than reported and reworked it (`30229be`–`ba54aff`).
3. Asked what of "left untested" it had closed, the agent found that its reasons for leaving things open didn't hold, and closed them (`c676373`–`e6cf424`).

## Result

| Check | Run (`4dfc4a6`) | Roast (`ba54aff`) | Third pass (`e6cf424`) |
|---|---|---|---|
| Tests | 47, 2.0 s | 63, 3.4 s | 77, 3.8 s (+6 s for the real-Godot test where Godot 4.7 is installed) |
| Godot in the tests | shell-script fake that ignored its arguments, plus a stubbed `_godot` | `FakeGodot`, an executable that reads `--path` and `-gjunit_xml_file` like Godot | also writes `screenshot.gd`'s PNG and layout where `--out` points; one test runs the real Godot |
| Real captures | 2 GUT runs | 5 GUT runs | 5 GUT runs, 5 windowed screenshot runs |
| Generated mutants killed ([`mutants.py`](../../tools/mcp/tests/mutants.py)) | 299/453 (66%) | 337/453 (74%) | 432/458 (94%); `screenshot` 0/101 → 95/105 |
| Bugs found in `godot_mcp.py` | 0 | 1 (`81c1b65`) | 3 (`89d486f`, `aeb1e0e`) |
| CI | none | `.github/workflows/tools.yml` | same; checked in a clean clone with an empty HOME, not yet run on GitHub |

Every pass: passes with `GODOT_BIN=/nonexistent`; Godot side unchanged (`--import` ok, `check_scripts.gd` 17/17, GUT 43/43, 0 orphans, no new `.gd`, `.uid` or `.import` files).

### Bugs

| Commit | Bug | Found by | Grade |
|---|---|---|---|
| `81c1b65` | A path outside the project raised `ValueError`; the MCP server masks it, so the agent got only "Error executing tool scene_tree" | a test over an MCP client session | ✅ Red before the fix (the agent got only "Error executing tool scene_tree"), green at it; `ToolError` is how the server passes a message on |
| `89d486f` | `screenshot` returned `ok: true` for a scene with a broken shader: `_ERR_RE` didn't know Godot's `SHADER ERROR:` prefix | a real windowed run with a broken `backdrop_blur.gdshader`; the prefix was found with `strings` on the Godot binary | ⚠ Real, the fix right, red then green; but the comment and commit message it adds ("headless runs never compile shaders") are false: a headless `--import` on 4.7.2 prints the `SHADER ERROR` |
| `aeb1e0e` | When `screenshot.gd` produced no frame, its own reason (`SCREENSHOT FAILED: ...`) never reached `errors`; the agent saw only exit-time ObjectDB messages | a real windowed run with a missing hover target | ✅ Red before (the first error was the ObjectDB warning), green at it; the reason is the last thing `screenshot.gd` prints before exit messages, well inside the 4000-character tail |

Each test was red on the commit before its fix.

## Red phase

`GODOT_MCP_PATH` = `git show <commit>:tools/mcp/godot_mcp.py`. Same result for every pass's suite.

| Commit | Tests | Expected (issue) | Result |
|---|---|---|---|
| `925a7ed^` | `files_changed_by_build` (9) | the restores-dirty-to-head and deletes-untracked rows fail | those 2 fail, 7 pass ✅ |
| `925a7ed` | same | pass | 9 pass ✅ |
| `5da9c8c^` | GUT missing, no JUnit + Godot error, export without presets | fail | 3 fail ✅ |
| `5da9c8c` | same | pass | 3 pass ✅ |
| `ad102ed^`, `ad102ed` | missing binary, timeout | pass on both (the refactor kept behavior) | 2 pass on both ✅ |

The real-Godot test also fails on a copy with `-gjunit_xml_file=` misspelled, as does its pinned-command counterpart.

## Surviving mutants (26 of 458)

| Mutants | Why they survive | Grade |
|---|---|---|
| Timeouts n+1: `30`, `600`, `300`, `1200`, `900`, `180` (6) | equivalent: a test can't tell 600 s from 601 s | ✅ No test can tell n seconds from n+1 |
| `"<deleted>"` marker, `errors="replace"` (2), the prefix of "Path escapes project" (4) | equivalent for the inputs the tool gets; tests match the reason, not the prefix | ❌ `"<deleted>"` and the prefix are equivalent, the two `errors="replace"` aren't: Python looks the handler up only on an invalid byte (`b"\xff".decode(errors="x")` raises `LookupError`), so one bad byte in a `.tscn` crashes `find_scenes` for the whole project |
| `_git_snapshot`: `if returncode != 0` / `return {}` removed (2) | equivalent: a failing git prints nothing on stdout, so the snapshot is empty either way | ❌ In a repo with no commits `git diff HEAD` exits 128 while `ls-files` succeeds and lists files: the mutant returns them, the code `{}`. Needs a test, and a decision on what that case should report |
| `_parse_tscn`: `split("=", 1)` → `split("=", 2)`; `screenshot`: `rsplit("/", 1)` → `rsplit("/", 2)` (2) | equivalent: the part used is the same | ✅ Only `[1]` / `[-1]` is used, the same for any maxsplit |
| `screenshot`: either `unlink` removed, `or` → `and` in the "both files exist" check (3) | equivalent: `screenshot.gd` writes the PNG and the layout together, and a stale pair is removed by the other `unlink` | ❌ The unlinks are equivalent, `or` → `and` isn't: `screenshot.gd` saves the PNG and then opens the layout, so a failed layout write or the 180 s timeout leaves the PNG alone, and the mutant crashes on `read_text` (the agent gets a bare "Error executing tool") |
| `screenshot`: `"SCRIPT ERROR"`, `"SHADER ERROR"`, `"USER ERROR"` in the project-error prefixes (3) | redundant with the `res://` test: every captured project error has an `at:` line with a `res://` path | ❌ Not for `SHADER ERROR`: a windowed 4.7.2 run with a shader built in code prints `at: (null) (:3)`, with no `res://`; without the prefix the error goes to `environment_errors` and `ok` stays true. `SCRIPT ERROR` is the same for a script built in code |
| `run_tests` `"USER ERROR"`, `screenshot` `"USER WARNING"` (2) | dead in Godot 4.7: the binary contains neither string (`strings`), they are Godot 3 prefixes | ⚠ True: `strings` finds neither, and the push-error capture prints `ERROR:`. But `push_error`, the case these prefixes stood for, now lands in `environment_errors`: `screenshot` of a scene that calls `push_error` returns `ok: true` |
| `_godot`: `"SHADER ERROR"` in the fatal prefixes (1) | equivalent for `build`: headless runs never compile shaders, so it never appears there | ⚠ The reason is false: headless `--import` compiles shaders (dummy renderer) and prints `SHADER ERROR` for a broken `backdrop_blur.gdshader`. Still equivalent: the `ERROR: Shader compilation failed.` that follows fails the step on its own |
| `_parse_tscn`: `current = None` on a new section removed (1) | unreachable: Godot 4.7 refuses a scene with a `[sub_resource]` after a node ("Parse Error: Invalid parameter"), checked by loading one | ✅ Godot refuses it (checked); the message is "Unknown tag 'sub_resource' in file", not "Invalid parameter" |
| `screenshot`: `parents=True` → `False` for `.godot/screenshots` (1) | equivalent in a real project: `.godot/` exists once the project has been imported | ❌ `.godot/` is gitignored: a fresh clone or worktree has none until the first import, so `screenshot` before `build` raises. The tests pass only because the `scenes` fixture creates `.godot/editor/` |
| `_godot`: tail length n+1 on the timeout path (1) | not tested; the finished-run path is | ❌ True, and a missing test: print more than 4000 characters before the timeout in `test_timeout_keeps_what_godot_printed` |

## Deviations from the issue

- **Run command**: `pytest --import-mode=importlib tools` instead of `pytest tools/mcp/tests`, so future suites under `tools/` run with it. The command is in `AGENTS.md` and CI; the issue body was updated to match.
- **No stubbed `_godot`**: the issue's "Stubbed `_godot`" seam was replaced by `FakeGodot` in the roast (mistake 7).
- **Added**: section 8 (the tool contract the skills rely on), 9 (over MCP), 10 (`screenshot`), 11 (real Godot), CI.

## Mistakes and the rules they became

| # | What happened | Caught by | Rule | Grade |
|---|---|---|---|---|
| 1 | The Done criterion only knew "red on `<sha>^`", which turned 5 of 47 tests red | reading the criterion against the plan | `94ffe62`: red for behavior no commit broke | ✅ Red on a generated mutant is how a test of existing behavior is seen red |
| 2 | Helpers in `conftest.py` imported from the test file fail under `--import-mode=importlib` | before the first run | `94ffe62`: fixtures in `conftest.py`, helpers in the test file | ✅ Names the `--import-mode=importlib` limit and where each kind of code goes; the suite follows it |
| 3 | Fixture lines selected by `.endswith(...)`; real lines end with an ANSI reset code | first run: the test's own guard assert | `94ffe62`: select lines by their text | ✅ The suite follows it |
| 4 | Git setup passed only `-c user.name/email`; global config (signing, hooks) could still apply | review, not observed | `94ffe62`: `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_NOSYSTEM`, `GIT_CEILING_DIRECTORIES` | ✅ Shuts out the global and system config and repos above `tmp_path`; the suite passes with them set |
| 5 | Older copies of `_godot` take `(args, timeout)` | reading the red-phase commits | `94ffe62`; moot after the roast (no stubs) | ✅ Moot: no stubs |
| 6 | **Reported "26/26 mutations killed".** The 26 were picked by the test author after writing the tests. Generated mutants: 299/453 | roast | `eea0993`: generated mutants, `mutants.py` in Done | ✅ Reproduced: 432/458, the same 26 survivors; the measure no longer depends on what the author picks |
| 7 | No command line was checked: the fake ignored argv, the stub wrote JUnit whatever the flags. A broken `-gjunit_xml_file`, `--path` or `--headless` passed | roast, generated mutants | `eea0993`: the seam is the process; pin argv to commands proven on real Godot | ✅ The fake reads `--path`, `-gjunit_xml_file` and `--out`, so a wrong flag loses its results; argv is pinned to the captures |
| 8 | `test_gut_missing` passed with the GUT check deleted (it asserted only keys and `ok`) | roast, generated mutants | `30229be`: the exact result, and Godot never started | ⚠ The Rule cell is a test commit, not a rule; what stops a repeat is `mutants.py` in Done (#6), which would catch a weak assertion |
| 9 | Hand-written data where Godot's behavior was unknown (an empty run's JUnit, an ERROR inside a passing test) | roast | `eea0993`: capture first. The capture showed GUT fails such a test itself | ⚠ The rule is right, but the suite breaks it: `USER ERROR: boom` (a prefix 4.7 never prints) and the project `WARNING` are written by hand, and only the second says that no capture has it |
| 10 | The tool-parameter test was a schema snapshot: an optional parameter turned it red | roast | `eea0993`: contract as a subset | ✅ A subset check: red on a removed or a newly required parameter, green on a new optional one |
| 11 | All 47 tests written in one pass, red seen afterwards: the horizontal slicing `tdd` warns against | roast | none: acceptable for characterising existing code, recorded here | ✅ No rule needed: Done's red-on-a-mutant is how a characterisation test is seen red |
| 12 | The mutation runs left ~240k temp files and exhausted `/tmp`'s inodes | `No space left on device` | `fc1c5d1`: `mutants.py` removes each run's temp dir | ✅ `finally: rmtree` per run; this grading run left no `tmp-*` behind |
| 13 | **`screenshot` left untested "because it needs a windowed Godot and a display".** Only Godot needs them; the tool's logic didn't. Testing it found 2 bugs | the user asking why it was left | `e6cf424`: what Godot needs is the fake's to stand in for | ✅ It found 2 bugs on its first use, and holds for any tool that runs Godot |
| 14 | "Possibly dead, unverified" (`USER ERROR`) and "unreachable" (`current = None`) reported without checking the engine. Checking took two commands, and the `strings` check turned up `SHADER ERROR` | the same question | `e6cf424`: check "dead" / "unreachable" on the engine before reporting it | ⚠ It names only "dead" and "unreachable"; the same unchecked engine claims came back as "equivalent" and "redundant" (headless shaders, `res://` on every error), and both are false. It should cover every survivor reason that is a claim about Godot |
| 15 | Command lines pinned to runs made once by hand, with nothing re-running them | the same question | `e6cf424`: the real-Godot test, run wherever Godot 4.7 is installed | ⚠ Only `build` and `run_tests` are re-run: `screenshot`'s command line is still pinned to hand runs, and `--export-release` never ran on a Godot (no capture, the real test doesn't export) |

## Left untested

- The real windowed `screenshot` run: its output is replayed from captures; a test opening windows on every run was not added.
- `godot.build` can't catch a broken shader: headless Godot doesn't compile shaders. Only `screenshot` sees it (`89d486f`).
- `tools/design/figcraft.py`: no suite yet.

## Grading

Grade columns are filled by the grader, not the agent that wrote the tests: per row ✅, ❌ or ⚠, with one line of why.

- **Bugs**: real, and the fix right? `git show <commit>` for the fix; red on the code before it:
  `git show <commit>^:tools/mcp/godot_mcp.py > /tmp/before.py`, then
  `GODOT_MCP_PATH=/tmp/before.py uv run --with pytest --with 'mcp>=2.3,<3' pytest --import-mode=importlib tools -k <test in the commit>`.
- **Surviving mutants**: is the reason true? ❌ means a missing test.
- **Mistakes**: does the rule stop it next time, without a new mistake?
- **Numbers**: `uv run --with pytest --with 'mcp>=2.3,<3' python -I tools/mcp/tests/mutants.py . /tmp/mutants` gives 432/458 (~2.5 min); the suite as in `AGENTS.md`, once with `GODOT_BIN=/nonexistent`.

Each ❌ becomes a test, a fix or a rule in the skill, as in the other evals.

### Grader's notes

Two findings that sit in no row:

- **`godot.build` does catch a broken shader.** "Left untested" says it can't. A headless `--import` of a `git archive` copy with `COLOR = undefined_thing;` in `backdrop_blur.gdshader` prints `SHADER ERROR` and then `ERROR: Shader compilation failed.`, and `_godot` returns `ok: false` for the step. An incremental import after editing the shader does the same. The headless `at:` line is `(null) (:12)`, with no `res://`.
- **A scene's `push_error` is filed as machine noise.** Godot 4.7 prints `push_error` / `push_warning` as `ERROR:` / `WARNING:` with `at: push_error (core/...)`. The `res://` appears only in the backtrace, which `_parse_errors` skips, so `screenshot` puts the error in `environment_errors`. Checked on the `push-error` capture: `project` is empty. Probably a bug, and the one the dead `USER ERROR` prefix was meant to catch.
