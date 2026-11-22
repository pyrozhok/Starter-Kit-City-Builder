---
name: review-pr
description: Review a PR, branch or local diff: Godot gates, mattpocock code-review, then the Godot checklist.
disable-model-invocation: true
---

# Review PR

Argument: PR number/URL, branch name, or nothing (uncommitted changes).

## 1. Get the change

PRs live on the fork: pass the repo flag from `docs/agents/issue-tracker.md` to every `gh` command.

- PR: `gh pr view <n>` (`--json title,body,baseRefName,headRefName,headRefOid,commits`) and `gh pr diff <n>`.
  Gates need the PR's code locally: if the current branch's HEAD equals `headRefOid`, use it; otherwise
  `gh pr checkout <n>` on a clean tree, and ask first when the tree is dirty.
- Branch: base is `main`; `git log main..HEAD` and `git diff main...HEAD`.
- Local: base is `HEAD`; `git diff HEAD`.

Done when you know the base, the commit list, and the PR's stated intent (its description; empty
description is itself a nit).

## 2. Gates

- `godot.build`: `ok: true` and `files_changed_by_build` empty. Each listed file is either PR churn
  (its `.import`/`project.godot` disagree with the engine) or a `GODOT_BIN` that isn't the engine
  version in `AGENTS.md` — check `godot --version` and say which. Restore those files
  (`git checkout -- <files>`) so the review leaves the tree as it found it.
- `godot.run_tests`: `ok: true`, `orphans: 0`. Note each behavior change in the diff that no test covers.

Done when both results are recorded and `git status` matches step 1.

## 3. General review

Invoke `mattpocock-skills:code-review` with the base from step 1 as the fixed point. If that skill
isn't available, stop and tell the user to install the plugin (see `AGENTS.md`). Keep its findings for the
report; the checklist below covers only what it can't know about Godot and this project.
Done when its Standards and Spec findings are in hand.

## 4. Godot checklist

Apply every item to the diff; done when each one is marked pass, fail (with `path:line`) or n/a.
Terms follow `GLOSSARY.md`.

Commits

- Each commit's diff matches its message — subject **and body** (`git log -1 --format=%B <sha>`):
  a change the body describes is covered. A `fix:` touches only the fix and its test, a `chore:`
  changes no behavior. Model: upstream `3a6e666` — "fixes memory leak" is exactly one added
  `n.queue_free()` in `update_structure()`.

GDScript

- Declarations are typed wherever the type is known.
- A node removed from the tree is also `queue_free()`d (pattern: `update_structure()`).
- `_process` only reads input and moves the selector; instancing and allocation happen on events —
  the preview is rebuilt only when `index` changes (`action_structure_toggle()`).
- Every new input action is declared in `project.godot` `[input]`; one-shot actions use
  `is_action_just_pressed`.
- Build on a tile already holding the same structure costs nothing; demolish leaves `-1`;
  save → load restores position, orientation and structure index.
- `Builder.structures` keeps its order (append new structures at the end): the structure index is
  positional, so reordering breaks saved maps and `sample map/map.res`.
- UI talks to the game through `@export` references and signals; each signal is connected once and
  dies with its owner.
- New interactive Controls come with the `gui_get_hovered_control()` guard in `action_build` /
  `action_demolish` (see `generate-ui`) — otherwise clicking the Control also builds.

Scenes and resources (`.tscn`, `.tres`, `.import`, `project.godot`)

- Every `ext_resource path=` exists; ids are unique; existing `uid=` values are unchanged.
- Every new script/resource has its `.uid` file committed.
- UI values (colours, StyleBoxes, fonts, sizes, margins) live in `scenes/ui/theme.tres` type variations,
  reached by `theme_type_variation`; a `.tscn` carrying `theme_override_*` or an inline `StyleBox*`/`Color(`
  is a fail (rule: `generate-ui/mockup.md`, check: its `grep`, run on every changed `.tscn`).
- Only source files are committed: `*.tmp`, `export_presets.cfg`, `.godot/`, `build/` stay out.
- `project.godot` changes are intentional: `config/features` matches the engine version in
  `AGENTS.md`, settings hold no machine-local paths, every enabled plugin is wanted.
- Binary assets (`.glb`, `.png`, `.ogg`) change only in a PR about assets.

## 5. Report

Before writing the report:
- Every finding is verified before it's reported: read the code path or reproduce it.
  Unverified → put it under **Unverified** instead of Blocking/Nits.
- Every proposed fix is checked to work: for GDScript, the fixed code must still compile
  against the members it uses (`godot.build`); for refactors, show that behavior is unchanged;
  for types: the narrowest existing type, adding a class_name if needed;
  for Python in `tools/`: the pytest suite (command in `AGENTS.md`); a finding about old behavior is
  shown red on the old code with `GODOT_MCP_PATH` (see `write-pytest`).
- GUT asserts don't abort the test: the lines after a failed assert still run. Don't suggest moving
  cleanup out of a test body on that ground.
- Decisions already explained — in a code comment at that spot, `docs/adr/`, or a graded finding
  in `evals/review-pr/` — stay settled: cite the explanation and raise them again (in any list,
  judgement calls included) only with new evidence against it.

Three lists, most severe first, one line each: `path:line — problem — concrete fix`.
**Blocking**: bugs, broken resources, failing gates. **Nits**: the rest. **Unverified**: findings
you couldn't confirm, with what would confirm them. Then gate results, the
`mattpocock-skills:code-review` findings worth acting on, and what headless runs can't verify (visuals, feel, audio).
If nothing blocks, say so plainly.

Post to GitHub (`gh pr review <n> --comment|--request-changes`) when the user asks for it.
