## Engine

Godot **4.7** — the single source for the engine version (`config/features` in `project.godot` matches it).
`GODOT_BIN` (the environment; `.mcp.json` passes it through as `${GODOT_BIN:-godot}`) must run a 4.7 binary: any other version rewrites `*.import` on every build.

## Agent skills

Requires the plugin `mattpocock-skills@claude-plugins-official` (enabled in `.claude/settings.json`;
install: `/plugin install mattpocock-skills@claude-plugins-official`). Project skills call its skills
by their prefixed name (`mattpocock-skills:code-review`, `mattpocock-skills:tdd`); if one is missing,
stop and ask the user to install the plugin.

### Issue tracker

GitHub Issues on the fork `pyrozhok/Starter-Kit-City-Builder` (always pass `--repo`; `origin` is upstream). See `docs/agents/issue-tracker.md`.

### Triage labels

Default five labels: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: root `GLOSSARY.md` + `docs/adr/`. See `docs/agents/domain.md`.

## Python tools

`tools/*.py` are uv scripts (dependencies in their PEP 723 header). Tests (no Godot needed; skill
`write-pytest`): `uv run --with pytest --with 'mcp>=2.3,<3' pytest --import-mode=importlib tools`
CI (`.github/workflows/tools.yml`) runs the same command on PRs that touch `tools/`.

## Git workflow

- `main` on the fork changes only through a merged PR.
- One branch per task, cut from a fresh `fork/main`: `feat/…`, `fix/…`, `docs/…`, `chore/…`.
- Atomic Conventional Commits; PRs merge with a merge commit, never squashed.
- Push and merge only after the user's explicit "yes" to that step.
- Before a merge: `/review-pr <n>` in a fresh session.
