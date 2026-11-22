# review-pr eval 005: recall on 5 PRs with planted bugs

- **Target**: PRs [#32](https://github.com/pyrozhok/Starter-Kit-City-Builder/pull/32)–[#36](https://github.com/pyrozhok/Starter-Kit-City-Builder/pull/36) on `pyrozhok/Starter-Kit-City-Builder`, each cut from `fork/main` `ffec0c5`. 7 planted bugs across 4 PRs; #36 is clean.
- **Why**: runs 001–004 graded precision only. This run counts the bugs the agent missed ([#23](https://github.com/pyrozhok/Starter-Kit-City-Builder/issues/23)).
- **Date**: 2026-11-22
- **Setup**:
  - One session built the 5 PRs and wrote the answer key. The key stayed outside the repo until all reviews were finished.
  - Each review was a fresh headless `claude -p "/review-pr <n>"` session (Opus 5.5) in its own detached worktree. Review times: 82–125 s.
  - A separate session graded each report against the key. The user approved the grades on 2026-11-22.
- **The bugs are on purpose.** The PRs were closed after grading and their branches deleted; none was meant to merge.

## Answer key

- **A #32** `refactor/zoom-limits` (`91d326f`) "refactor(view): zoom limits and step as exported settings"
  - A1 `zoom_in`: `zoom = min(min_zoom, zoom - zoom_step)`: `min` instead of `max`, so zoom drops to ≤15 and keeps falling instead of clamping.
  - A2 `zoom_out`: `zoom = max(max_zoom, zoom + zoom_step)`: `max` instead of `min`, so zoom jumps to ≥80 with no upper clamp.
  - (Not scored: `test_zoom_in_moves_camera_closer` only asserts that zoom decreased, so it passes on A1.)
- **B #33** `feat/hud-top-bar` (`7a9c79b`) "feat(ui): dark bar behind the cash display"
  - B1 the TopBar Panel (1920×130) keeps the default `mouse_filter` (STOP), so build/demolish is blocked under the top strip.
  - B2 the style is hard-coded in `main.tscn` (`theme_override_styles` + inline `StyleBoxFlat`) instead of a `theme.tres` type variation (project rule).
- **C #34** `test/data-map-tests` (`b362ffe`) "test(data_map): cover new_map cash reset and structures after reload"
  - C1 `test_new_map_resets_cash_after_spending` never calls `Builder.new_map()`; it tests `DataMap.new()` defaults and can't fail for the behaviour it names.
  - C2 `test_saved_map_keeps_structures_after_reload` never saves, so the `if FileAccess.file_exists` branch never runs and no assertion runs.
- **D #35** `docs/orbit-docs` (`6e16dc1`) "docs(view): document orbit_speed"
  - D1 a behaviour change hidden in a docs commit: `orbit_speed` default 3.0 → 12.0. `test_auto_orbit_turns_camera_around_center` fails, so the gate is red.
  - D2 the doc comment says radians per second; the code adds it to `rotation_degrees`.
- **E #36** `test/zoom-tests`: clean, correct tests of the existing 15/80 zoom clamp. Any finding is false.

## Per PR

| PR | Planted | Found | Missed | Other findings: correct-unplanned / false | Wrong fix | Verified before reporting |
|---|---|---|---|---|---|---|
| A #32 zoom-limits | A1 min/max zoom_in, A2 zoom_out | A1, A2 (Blocking) | — | 3 / 0: weak test (`assert_lt` passes on the bug, the key's unscored weakness), no guard against min>max, commit says "no behaviour change" | 0 (both fixes correct; the zoom-out fix's temp test failed for a test-order reason and was labelled as reasoned only) | Yes: temporary red tests, fix applied, then reverted |
| B #33 hud-top-bar | B1 mouse_filter STOP, B2 inline StyleBox instead of theme.tres | B1 (Blocking) | **B2** | 3 / 0: fixed 1920 width vs `aspect="expand"` (checked in project.godot), hand-tuned 130 px height (judgement), hand-written sub_resource id (cosmetic). Contrast stated as unverified | 0 (`mouse_filter = 2`; not built, and said so) | Yes for B1: headless probe `filter=0 rect 1920x130` |
| C #34 data-map-tests | C1 never calls new_map, C2 never saves, asserts never run | C1, C2 (Blocking) | — | 3 / 0: misleading name, magic 10000, one blank line vs two | 0 | By reading code only (says so); no red run of the fixes |
| D #35 orbit-docs | D1 3.0→12.0 hidden in docs commit (test red), D2 radians vs degrees | D1, D2 (Blocking) | — | 1 / 0: `##` vs inline `#` comment style | 0 | Yes: gate run shows the named failing test; unit traced through `rotation_degrees` |
| E #36 zoom-tests (clean) | none | — | — | 0 / 4 Nits (no Blocking; verdict "nothing blocks" correct): `after_each` doesn't release zoom actions (no leak, `_tap` releases), unused loop var `i` warning, blank-line spacing, PR body lacks red/orphan note | n/a | Ran the after_each change (5/5) and reasoned the red check |

## Totals

| Metric | Value |
|---|---|
| Recall (planted bugs found) | 6/7 (missed B2) |
| Correct unplanned findings | 10 |
| False findings on bugged PRs | 0 |
| Clean PR #36 | false Blocking 0, false Nits 4 |
| Wrong fixes | 0 |
| Bugged PRs whose planted findings were verified by a run or probe | 3/4 (#34 read the code only, and said so) |

On the clean PR the verdict "nothing blocks" was correct. Its 4 Nits are style/process remarks and none claims a defect, but they are graded false.

## Findings

1. **Behavioural bugs are caught reliably, and with proof.** All six behaviour/test defects (A1, A2, B1, C1, C2, D1) plus D2 were Blocking with the right fix. A wrote temporary red tests; B ran a headless probe; D pointed at the gate's failing test. The skill's gates and "verify before reporting" carry the recall.
2. **The miss is a project-convention rule, not a bug.** B2 (style inlined in main.tscn instead of a theme.tres type variation) went unreported, though the same review cited `generate-ui/SKILL.md:40` for mouse_filter. The checklist sends the reviewer to the decorative-panel rule but not the theme rule; the 3 nits it did raise on the same node (width, height, id) show it looked at the StyleBox and didn't connect it to the rule.
3. **Subject/diff mismatch is a strength.** A ("refactor ... no behaviour change"), C (body claims coverage the diff lacks) and D (`docs:` with a default change) all failed the Commits check with the right reason.
4. **Weak tests are spotted even when unplanned.** A flagged that `assert_lt` passes on the bug; C saw both tests can't fail and that the reload branch never runs. Test-quality review works on test-only PRs.
5. **On a clean PR it stays quiet on Blocking but pads Nits.** E got "nothing blocks" (correct) but 4 nits, one stretching a builder-section rule to test_view.gd. Noise cost is low; precision on Blocking was 100% across all five PRs.
6. **Fix verification is uneven.** A ran its fixes; B, C and D proposed fixes without running them (B said the edit-and-probe was refused permission). None was wrong, but this matches 004's 0/4 fixes checked.

## Left open

- B2's miss: the checklist should send the reviewer to the `theme.tres` rule ([#37](https://github.com/pyrozhok/Starter-Kit-City-Builder/issues/37)). Done when a rerun on PR #33's case reports it.
- Nit padding on clean PRs (finding 5) and unchecked fixes (finding 6) have no rule yet.
- One run per PR, 5 PRs, all built by one session: rerun after every rule change before reading trends into it.
