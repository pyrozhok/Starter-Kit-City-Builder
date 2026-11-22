# review-pr eval 006: rerun of PR #33 after the theme.tres rule

- **Target**: [#33](https://github.com/pyrozhok/Starter-Kit-City-Builder/pull/33) `feat/hud-top-bar` (`7a9c79b`), the PR where [005](005-planted.md) missed planted bug B2.
- **Why**: [#37](https://github.com/pyrozhok/Starter-Kit-City-Builder/issues/37): review-pr's checklist had no theme.tres item. Done when a rerun reports B2.
- **Date**: 2026-11-22
- **Change under test**: one item in the checklist's *Scenes and resources* section: UI values live in `scenes/ui/theme.tres` type variations; `theme_override_*` or an inline `StyleBox*`/`Color(` in a changed `.tscn` is a fail (rule and grep: `generate-ui/mockup.md`).
- **Setup**:
  - As in 005: a fresh headless `claude -p "/review-pr 33"` session (Opus 5.5) in a detached worktree at `7a9c79b` (PR closed, branch deleted; the commit is still on the fork). The worktree's `SKILL.md` was replaced by the new one, so its tree started with that one edit.
  - The first try did nothing: `gh` needed approval that a headless session can't give. 005 didn't record its permission setup. The rerun allowed `gh pr view/diff`, read-only `git`, `grep`, `godot.build`, `godot.run_tests`, Read/Grep/Glob/Skill/Agent. Writing files and `gh pr review` were not allowed, so nothing was posted.
  - Graded by the session that ran it, against 005's answer key.

## Result

| | 005 | 006 |
|---|---|---|
| B1 mouse_filter STOP | Blocking | Blocking |
| B2 inline StyleBox instead of theme.tres | **missed** | **Blocking** |
| Other findings: correct-unplanned / false | 3 / 0 | 2 / 0 (fixed 1920 width, hand-tuned 130 px height) |
| Fix for B2 | n/a | correct: `TopBar` type variation in theme.tres, `theme_type_variation`, delete the sub_resource and override |
| Gates | pass | pass (build no churn; 51/51, 0 orphans) |
| Time / cost | 82–125 s per PR / not recorded | 102 s, 12 turns, $1.12 |

B2 as reported:

> `scenes/main.tscn:37,98` — **the style is inline instead of in the theme.** The commit adds an inline `StyleBoxFlat_topbar` with `Color(0.05, 0.07, 0.1, 0.55)` and a `theme_override_styles/panel`. The project checklist fails any changed `.tscn` that does this. The colour is also a rounded copy of the theme's `StyleBoxFlat_panel` base (`0.054902, 0.0745098, 0.101961`). **Fix:** add a `TopBar` type variation (base `Panel`) with this StyleBox to `scenes/ui/theme.tres`, set `theme_type_variation = &"TopBar"` on the node, and delete the sub_resource and the override.

## Findings

1. **One checklist line closes the miss.** B2 is Blocking with the right fix, and the review spotted that the inline colour copies the theme's panel colour, which is more than the rule asked for.
2. **The sub_resource-id nit from 005 went away.** It is now folded into the B2 fix.
3. **The recipe needs its permissions written down.** Without allowed tools a headless review stops at step 1. Later reruns should reuse the allow list above.

## Left open

- One run on one PR. #32 and #34–#36 weren't rerun, so this shows the rule works but not that it adds no noise elsewhere (for example on the clean #36).
