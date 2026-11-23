# review-pr eval 007: PR #33 through `tools/evals/run.py`

- **Target**: [#33](https://github.com/pyrozhok/Starter-Kit-City-Builder/pull/33) at `7a9c79b`, as in [006](006-pr33-theme-rule.md).
- **Why**: [#25](https://github.com/pyrozhok/Starter-Kit-City-Builder/issues/25): first real run of `uv run --script tools/evals/run.py review-pr 33`, the scripted form of 006's procedure.
- **Date**: 2026-11-23
- **Setup**: the script made the detached worktree, copied this checkout's review-pr skill into it (same skill as 006), imported, and ran `claude -p "/review-pr 33"` (Opus 5.5) with 006's allow-list. No permission denials; nothing posted. The gates ran, so the worktree's `.mcp.json` was used.

## Result

| | 006 | 007 |
|---|---|---|
| B1 mouse_filter STOP | Blocking | Blocking |
| B2 inline StyleBox instead of theme.tres | Blocking | Blocking |
| Other findings: correct-unplanned / false | 2 / 0 | 1 / 0 (fixed 1920 width) |
| Gates | pass | pass (build no churn; 51/51, 0 orphans) |
| Time / turns / cost | 102 s / 12 / $1.12 | 30 s / 7 / $0.55 |

B2 as reported:

> `scenes/main.tscn:37-38,98` — **The colour and StyleBox are set in the scene instead of the theme.** The PR adds a `StyleBoxFlat` and `theme_override_styles/panel` in `main.tscn`, which the checklist counts as a fail. Fix: move the StyleBox into `scenes/ui/theme.tres` as a type variation (e.g. `HudTopBar/styles/panel`), set `theme_type_variation = &"HudTopBar"` on `TopBar`, and delete the sub_resource from `main.tscn`.

## Left open

- This run didn't invoke `mattpocock-skills:code-review` (it said so), which likely explains the lower time and cost than 006.
- One run, one PR; graded by the session that ran it, against 005's answer key.
