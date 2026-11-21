---
name: write-pytest
description: pytest tests for this project's Python tools, the godot MCP server and figcraft.py. Use when adding or fixing a test under tools/, covering a bug in an MCP tool, or proving a tools/ fix red on the code before it.
---

# Write pytest (tools/)

Follow `mattpocock-skills:tdd` for the loop (if it isn't available, tell the user to install the
plugin — see `AGENTS.md`): every new test is seen **red** before it goes green. This skill adds what
is specific to pytest and the scripts in `tools/`. Terms follow `GLOSSARY.md`.

Run with the command in `AGENTS.md` (Python tools; CI runs the same); narrow it with a file path or
`-k <substring>`. Layout: `tools/<dir>/tests/test_<script>.py`, with `conftest.py` beside it.
Model: `tools/mcp/tests/`.

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
  `RESULTS_XML` and `SCREENSHOTS` from `ROOT`. Patch each one the test touches; `ROOT` alone leaves
  the others on the real project. Patch `ROOT` in every test: a copy loaded from `git show` has its
  `__file__` outside the repo.

## Seams in godot_mcp.py

Godot is another process; the seam is that process boundary. Never stub `_godot` or another
function of the module: a stub cooperates whatever arguments it gets, so the command line, the part
Godot actually receives, goes untested. What Godot needs to run (a display, a GPU, GUT) is the
fake's to stand in for, never a reason to leave a tool untested: `screenshot` needs a window only
inside Godot.

- **Fake Godot** (`godot` fixture, `FakeGodot` in `conftest.py`): an executable that does only what
  `godot_mcp` relies on Godot doing — finds the project through `--path`, writes JUnit where
  `-gjunit_xml_file` points, writes the PNG and layout where `--out` points, prints, changes files,
  exits, sleeps — and records each call's arguments. `on(when, ...)` adds a rule; `capture=` replays
  a real run from `fixtures/`. Pin `godot.calls` to command lines proven against real Godot (the
  ones the captures were taken with), not to what the code happens to build.
- **Real Godot**, where one is installed: the last test re-runs `build` and `run_tests` on Godot 4.7
  in a minimal project, so the pinned commands are checked against the engine, not only against
  the captures. Skipped without a 4.7 binary.
- **Temp git repo**, for `_git_snapshot` and `files_changed_by_build`: `git init` in `tmp_path`, one
  commit, `ROOT` patched to it. Set `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1` and
  `GIT_CEILING_DIRECTORIES=<tmp_path>` with `monkeypatch.setenv`, so neither the fixture nor the code
  under test sees the user's git config (signing, hooks) or a repo above `tmp_path`; commit with
  `git -c user.name=t -c user.email=t@t`.
- **Tool contract**, for the skills: `asyncio.run(mod.mcp.list_tools())`. A skill breaks when a tool
  or a parameter it passes is gone, or a new parameter becomes required; assert exactly that (the
  parameters skills pass ⊆ `properties`, `required` ⊆ them). An exact match of the schema is a
  snapshot: it goes red on a harmless optional parameter.
- **Over MCP**, for what the agent receives: `async with mcp.client.Client(mod.mcp) as c:
  await c.call_tool(name, args)`, in memory. A `dict` result arrives as JSON text in
  `content[0].text`, a list as `structured_content["result"]`. Only a `ToolError` keeps its message;
  any other exception reaches the agent as a bare "Error executing tool <name>".

`@mcp.tool()` returns the plain function: tests call `mod.build(...)` directly where the protocol
adds nothing.

## Fixtures

- Godot and GUT output is captured from a real run, never written by hand: throwaway test scripts
  or scenes in a `git archive HEAD | tar -x -C <scratch>` copy, Godot run there with the tool's
  arguments, saving stdout, stderr and the files it wrote (JUnit, layout) as one capture. Before writing data for a case, capture
  it: Godot's behavior there is the expected value (`push-error` showed GUT already fails the
  test; `shader-error` showed a prefix the parser didn't know). Name and version in the file name
  (`gut-9.7.1-<name>.*`, `screenshot-4.7.2-<name>.*`); `fixtures/README.md` lists each capture and
  its exit code. Home paths become `~/`, output dirs `<out>/`, the GPU `<GPU>`; ANSI codes stay, so
  select lines by their text.
- A case no real run produces (a defensive branch) says so in a comment in the test.
- Files under `tools/*/tests/` are text Godot doesn't import (`.txt`, `.xml`, `.json`). A test
  writes the scenes, scripts and images it needs into `tmp_path`.

## Red

- **A fix that is already in**: run the suite on the file as it was before it.

  ```
  git show <sha>^:tools/mcp/godot_mcp.py > <scratch>/before.py
  GODOT_MCP_PATH=<scratch>/before.py <run command> -k <test>
  ```

  Red on `<sha>^`, green on `<sha>`. For a refactor the same tests are green on both sides, the
  evidence it kept behavior. Record each run (commit, tests, red or green) in the PR description.
- **Behavior no commit broke**: generated mutants, `tools/mcp/tests/mutants.py` (fixed AST
  rules, each mutant loaded through `GODOT_MCP_PATH`). Mutations picked by hand measure what the
  author already expects the tests to catch. Each survivor is either equivalent (a timeout n+1, an
  internal marker string: name it) or a missing test. "Dead" or "unreachable" is a claim about
  Godot: check it on the engine before writing it down (`strings` on the binary for a message
  prefix, loading the file in Godot for a scene layout).

## Done

- Each new test was seen red (on the unfixed code, `<sha>^` or a mutant), then green.
- The full suite passes with `GODOT_BIN=/nonexistent` (no test reaches a real Godot) and, where
  Godot 4.7 is installed, without it (the real-Godot test runs).
- `mutants.py` run; every survivor is equivalent, by name and reason, or has a test.
- `git status` shows no new `.gd`, `.uid` or `.import` files; `godot.build` and `godot.run_tests`
  still pass.
- Report the behaviors covered and the ones left untested, each with the reason it can't be tested.

Commits: `test(tools): …`. A bug a test finds gets its own `fix(tools): …` commit with that test.
Production code changes only for the fix under test; ask before reshaping it for testability.
