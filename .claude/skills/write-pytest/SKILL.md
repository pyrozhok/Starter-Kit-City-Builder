---
name: write-pytest
description: pytest tests for this project's Python tools, the godot MCP server and figcraft.py. Use when adding or fixing a test under tools/, covering a bug in an MCP tool, or proving a tools/ fix red on the code before it.
---

# Write pytest (tools/)

Follow `mattpocock-skills:tdd` for the loop (if it isn't available, tell the user to install the
plugin — see `AGENTS.md`): every new test is seen **red** before it goes green. This skill adds what
is specific to pytest and the scripts in `tools/`. Terms follow `GLOSSARY.md`.

Run with the command in `AGENTS.md` (Python tools); narrow it with a file path or `-k <substring>`.
Layout: `tools/<dir>/tests/test_<script>.py`, with `conftest.py` beside it. Model:
`tools/mcp/tests/`.

When the work comes from an issue with a test plan (e.g. #2), the plan's sections are the agreed
seams: follow them, and ask only where the code contradicts the plan.

## Loading a script

`tools/*.py` are uv scripts (PEP 723 header), not a package, so `import godot_mcp` fails. A
function-scoped fixture in `conftest.py` loads a fresh module per test with
`importlib.util.spec_from_file_location`, from `$<SCRIPT>_PATH` (`GODOT_MCP_PATH`, `FIGCRAFT_PATH`)
when set, otherwise from the file in `tools/`. Under `--import-mode=importlib` a test file can't
import from `conftest.py`: fixtures go there, plain helpers in the test file.

- The run command's `--with` list matches the scripts' PEP 723 dependencies: `godot_mcp.py` builds
  its `MCPServer` at import.
- Module constants are computed once, at import: `GODOT` from `GODOT_BIN`, `ROOT` from `__file__`,
  `RESULTS_XML` and `SCREENSHOTS` from `ROOT`. Patch each one the test touches
  (`monkeypatch.setattr(mod, "RESULTS_XML", tmp_path / "results.xml")`); `ROOT` alone leaves the
  others on the real project. Patch `ROOT` in every test: a copy loaded from `git show` has its
  `__file__` outside the repo.

## Seams in godot_mcp.py

Godot never runs. Pick the seam by what the test observes:

- **Fake Godot**, for `_godot` itself (exit code, timeout, output parsing) through a real
  `subprocess`: patch `GODOT` to an executable shell script in `tmp_path` that prints a given stdout
  or stderr, exits with a given code, or sleeps. Missing binary: a path that doesn't exist.
- **Stubbed `_godot`**, for a tool (`build`, `run_tests`, `screenshot`):
  `fake(args, timeout, headless=True)` returns the dict a run returns and does what Godot would:
  writes the JUnit file to `RESULTS_XML`, changes files in the repo, writes the PNG and
  `.layout.json`. Assert on `args` where the tool's job is the command line (`script=` →
  `-gdir` / `-gselect`).
- **Temp git repo**, for `_git_snapshot` and `files_changed_by_build`: `git init` in `tmp_path`, one
  commit, `ROOT` patched to it. Set `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1` and
  `GIT_CEILING_DIRECTORIES=<tmp_path>` with `monkeypatch.setenv`, so neither the fixture nor the code
  under test sees the user's git config (signing, hooks) or a repo above `tmp_path`; commit with
  `git -c user.name=t -c user.email=t@t`.
- **Tool list**, for what agents see: `asyncio.run(mod.mcp.list_tools())` gives each tool's `name`
  and `input_schema["properties"]`. Pin the names and parameters the skills call (`run_tests`
  `script`, `test_name`; `scene_tree` `scene`): a rename breaks every skill that calls it.

`@mcp.tool()` returns the plain function: call `mod.build(...)` directly. A stub keeps the signature
`fake(args, timeout, headless=True)`: older copies call `_godot(args, timeout)`.

## Fixtures

- Godot and GUT output in a fixture is captured from a real run: throwaway test scripts in a
  `git archive HEAD | tar -x -C <scratch>` copy, Godot run there with `run_tests`' arguments. The
  file name carries the version (`gut-9.7.1-…`); `fixtures/README.md` says how each was made. Home
  paths become `~/`; ANSI codes stay, so select fixture lines by their text, not by how they end.
- Files under `tools/*/tests/` are text Godot doesn't import (`.txt`, `.xml`, `.json`). A test
  writes the scenes, scripts and images it needs into `tmp_path`, so `godot.build` and the real
  `find_scenes` never see them.

## Red for a fix that is already in

Run the suite against the file as it was before the fix:

```
git show <sha>^:tools/mcp/godot_mcp.py > <scratch>/before.py
GODOT_MCP_PATH=<scratch>/before.py <run command> -k <test>
```

Red on `<sha>^`, green on `<sha>`. For a refactor commit the same tests are green on both sides —
the evidence it kept behavior — so test through functions that exist on both. Record each run
(commit, tests, red or green) in the PR description.

Behavior no commit ever broke: a copy with that one behavior broken by hand (a `str.replace` on
the source, asserted to match once), loaded the same way. Every mutation turns at least one test
red; one that stays green is a missing test.

## Done

- Each new test was seen red (on the unfixed code, `<sha>^` or a mutated copy), then green.
- The full suite passes with `GODOT_BIN=/nonexistent`: no test reaches a real Godot.
- `git status` shows no new `.gd`, `.uid` or `.import` files; `godot.build` and `godot.run_tests`
  still pass.
- Report the behaviors covered and the ones left untested (the windowed screenshot run, real GUT).

Commits: `test(tools): …`. A bug a test finds gets its own `fix(tools): …` commit with that test.
Production code changes only for the fix under test; ask before reshaping it for testability.
