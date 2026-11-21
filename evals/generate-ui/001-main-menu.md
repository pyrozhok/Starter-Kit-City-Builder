# generate-ui eval 001: main menu from a figcraft mockup, first run

- **Target**: `design/main_menu.figcraft`, frames `MainMenu` (has a save) and `MainMenu_NoSave` (no save, New Game hovered); references `design/main_menu.png`, `design/main_menu_nosave.png`.
- **Scope**: first run of the "input: mockup" branch, with the cuts agreed before the run (one tip, static "just now", blur kept only if it works). Follow-ups: #3.
- **Date**: 2026-11-21
- **Skill version**: `.claude/skills/generate-ui/` at `ad1ab10` (SKILL.md + mockup.md) for the run; `0b1c590` adds this run's lessons.
- **Tools**: `godot.screenshot` and `tools/design/figcraft.py` from `64d30d1`. The figcraft MCP was not connected, so the layer tree came from `figcraft.py tree`.
- **Graded by**: the user, after a manual check of the game: #1–#11 ✅ (#3–#10 expected, #11 a correct escalation).

## Run

| Step | Result | Time |
|---|---|---|
| 1. Parse | Layer → node table from `figcraft.py tree` (in the plan), approved with changes. `design/main_menu.map.json` written in iteration 1, when the diff first needed it (step 1 asks for it up front; see "Deviations"). | before 16:20 (plan) |
| 2. Build | `chore(display)` … `feat(game)`: `9b63a3a`–`ce4fa1c`. Grep check for hard-coded values in `scenes/ui/*.tscn`: empty. | 16:20 → 16:29 |
| 3. Screenshot | Both states `ok: true`, ~2.4 s each (90 frames). Only environment errors ("leaked at exit"; also seen in GUT runs, so not project-specific). | |
| Stop: shown to the user | Iteration 0 approved by eye, with decisions: day scene stays, Shade darker at the top, title shadow blur expected. | |
| 4–5. Iteration 1 | Geometry 25/31 → 28/31 within ±2px; values 33/33 → 32/33 exact (Shade, #6, on purpose); fixes in `c249aa1`. No non-expected rows left, so no iteration 2. | 16:33 → 16:36 |

**Iterations used: 1 of 3.**

## Screenshots

| Iteration | Has save | No save, New Game hovered |
|---|---|---|
| Mockup | `design/main_menu.png` | `design/main_menu_nosave.png` |
| 0 | `evals/generate-ui/001/iter0_main_save.png` | `evals/generate-ui/001/iter0_main_nosave_hover-NewGame.png` |
| 1 (final) | `evals/generate-ui/001/iter1_main_save.png` | `evals/generate-ui/001/iter1_main_nosave_hover-NewGame.png` |

## Mismatches

Geometry from `figcraft.py diff design/main_menu.figcraft MainMenu <layout.json> design/main_menu.map.json` (31 mapped layers, same result in both states). Values from parsing `scenes/ui/theme.tres` against the figcraft nodes (33 values: colours, sizes, radii, paddings, gaps, the Shade gradient).

| # | Element | Property | Mockup | Iter 0 | Iter 1 | Fixed? | Expected? | Grade |
|---|---|---|---|---|---|---|---|---|
| 1 | Title (44) | rect x / w | 413 / 1094 (hugs text) | 0 / 1920 (full-width label) | 413 / 1094 | Yes: centre anchors, hugs text | — | ✅ |
| 2 | Tips/Text, Line1, Line2 (82–84) | width | 298 (fills row) | 248 | 298 | Yes: EXPAND_FILL | — | ✅ |
| 3 | Tips/Text (82) | height | 56 | 59 | 59 | No | Yes: Godot line height = ascent + descent (24px → 29, 20px → 24) | ✅ expected |
| 4 | Tips/Header, Divider, Body (73–80) | y | — | +2px | +2px | No | Yes: same cause as #3, within ±2px | ✅ expected |
| 5 | Notifications Item2 Text/Time (94/95) | x / w | Time 67px wide ("12 min ago") | 55px, Δx +12 ("just now") | same | No | Yes: relative time cut from the run → #3 | ✅ expected |
| 6 | Shade (43) | gradient | #0a0e14 α0 → α0.65 | same as mockup | α0.45 → α0.75 | Yes, against the mockup on purpose | Yes: the live day scene is brighter than the mockup's night sky; without it the title and disabled buttons read worse than in the mockup | ✅ expected |
| 7 | Background (42) | sky colour | dark blue evening image | grey-blue day scene | same | No | Yes: the live scene replaces the placeholder image (user decision) | ✅ expected |
| 8 | Title (44) | shadow | drop shadow (0,6) blur 18 | hard (0,6), no blur | same | No | Yes: Godot Label shadows don't blur; no workaround (user decision) | ✅ expected |
| 9 | Button labels, headers | letter-spacing | 2% / 4% (0.6–1px) | 1px | same | No | Yes: Godot glyph spacing is whole pixels | ✅ expected |
| 10 | Tip image (81) | content | "TIP IMAGE" placeholder | rendered `building-small-a` | same | — | Yes: real content replaces the placeholder | ✅ expected |
| 11 | Disabled Continue/Load icon (103/111) | opacity | 1.0 in the NoSave frame, 0.35 in component `State=Disabled` | 0.35 | 0.35 | No | **Needs a human**: the frame's instances lost the component's override; the agent followed the component. User: the component is right | ✅ correct escalation |

Values pass: 32 of 33 theme values equal the mockup (button states, bar colour/width, radii, paddings, gaps, font colours and sizes, divider, dot, title); the 33rd is the Shade gradient, changed on purpose (#6).

## Needs a human

- Disabled icon opacity (#11): which one is right, the component or the frame? **Resolved: the component** (0.35).
- Hover feel, the orbit speed (6°/s), backdrop blur strength over the moving city (shader `lod 3`), and how readable the text is as the camera turns. A still frame can't show these.
- **Manual check (user)**: orbit speed 6°/s → 3°/s (`8b00598`, now `View.orbit_speed`, an `@export`); the rest (hover, New Game, building, F1 → "Map saved", Continue after a restart) is OK.
- Keyboard focus: the focus style is the accent bar without the hover fill; not in the mockup.

## Summary

- 1 of 3 fix iterations; geometry 28/31 within ±2px, theme values 32/33 exact; every remaining row is expected or escalated, and all 11 rows were graded ✅.
- One manual-check change after the eval: orbit 6°/s → 3°/s.
- Removed a test that was never red (the load → new game → save → load cache case: not a bug in Godot 4.7), per write-test's "seen red, then green".
- Side fix: `e297f75` (reloading restores the saved cash).

## Skill and tool changes from this run

In `0b1c590` (mockup.md):
- Line height is listed among the expected mismatches (#3, #4).
- Text layers that hug their text map to Controls that hug too (#1: otherwise the rect can't be checked).
- Compare each state frame's instances with the component, and send any drift to the user (#11).
- Nodes created at runtime get stable names in mockup order (`Item1` on top) so `map.json` can address them.

In the run commits: `design/.gdignore` (`64d30d1`) and `evals/.gdignore` (`c249aa1`) stop Godot from importing mockups and eval PNGs.

Candidates, not done:
- The values pass and the side-by-side PNGs were one-off scripts in the session scratchpad. A `figcraft.py values` subcommand (theme.tres against the component layers) would make pass 2 repeatable.
- Step 1 should produce `map.json` before the build, as written; this run produced it at step 4.

## Deviations from the skill

- `map.json` was written at step 4, not step 1.
- `godot.screenshot` was called through Python (`uv run … godot_mcp.screenshot`), because the running MCP server was started before the tool existed; the code path is the same.

## Side findings (not UI)

- `fix(builder)` `e297f75`: F2 after building without saving restored the tiles but kept the spent cash (ResourceLoader cache returned the live map). A second suspected case (load → new game → save → load) was tested and is not a bug in Godot 4.7: saving refreshes the cache. That test was dropped because it was never red.
