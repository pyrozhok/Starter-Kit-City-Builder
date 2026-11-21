## Engine

Godot **4.7** — the single source for the engine version (`config/features` in `project.godot` matches it).
`GODOT_BIN` (in `.mcp.json` or the environment) must run a 4.7 binary: any other version rewrites `*.import` on every build.

## Agent skills

### Issue tracker

GitHub Issues on the fork `pyrozhok/Starter-Kit-City-Builder` (always pass `--repo`; `origin` is upstream). See `docs/agents/issue-tracker.md`.

### Triage labels

Default five labels: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: root `GLOSSARY.md` + `docs/adr/`. See `docs/agents/domain.md`.
