# Input: a mockup

The mockup is the **reference**: every size, gap, colour and font comes from its layer tree, not from
eyeballing the PNG. Build steps, `.tscn` rules and the input guard in `SKILL.md` still apply.

Inputs live in `design/`: `<name>.figcraft` (source), `<name>.png` / `<name>_<state>.png` (one export per
state), `<name>_components.png`. Exported icons are under `sprites/ui/`.

## 1. Parse

- Layer tree: the figcraft MCP if it is connected; otherwise
  `uv run --script tools/design/figcraft.py tree design/<name>.figcraft` (lists frames), then
  `… tree design/<name>.figcraft <Frame>` (absolute x/y/w/h, fills, strokes per side, radius,
  auto-layout, constraints, font, effects).
- Skip layers named `Label: …` (designer annotations) and image fills that stand in for content the game
  renders itself (a background placeholder, a screenshot).
- Write the table **layer (id) → mockup values → Godot node → theme item**: auto-layout → `HBox/VBoxContainer`
  `separation`, padding → StyleBox `content_margin_*` or `MarginContainer`, constraints → anchors/grow,
  component → its own `scenes/ui/<component>.tscn`, component state → StyleBox/colour per Control state
  (`normal`/`hover`/`disabled`/`focus`), stroke on one side → `border_width_<side>`, gradient →
  `GradientTexture2D`. Name each value that Godot cannot express exactly (letter-spacing below 1px,
  shadow blur, backdrop blur, line height: Godot sizes a line as ascent + descent, 1–3px taller than
  the mockup's "auto"): these are **expected mismatches**.
- A text layer that hugs its text maps to a Control that hugs too (centre anchors, `grow_horizontal`
  both), not a full-width Label with centred text: only then can its rect be checked.
- Instances in state frames can drift from their component (an override lost or added). Compare each
  state frame's instance values with the component state; the component wins, and each drift goes in the
  report under **needs a human**.
- Write `design/<name>.map.json`: `{"<layer id>": "<node path from the scene root>"}` for every layer
  with geometry worth checking. Nodes created at runtime (list items) get names from the code, in mockup
  order (`Item1` on top), so the path is stable.

Done when the table covers every non-annotation layer of every state frame, and the user has seen it.
**Stop and wait** for their answer before step 2.

## 2. Build

- Scene in `scenes/ui/`, components as their own scenes. All values in **one** `scenes/ui/theme.tres`:
  base types plus type variations (`theme_type_variation`) per mockup component. Nodes carry a
  variation, not `theme_override_*`.
- The scene root implements `_preview_state(state: String)`: one state per mockup frame (e.g. `save`,
  `nosave`). It sets the inputs the real game would set, through the same public API, so the screenshot
  shows a real state, not a mock.
- UI → game only through signals; the scene that owns both sides connects them (`SKILL.md` §2).

Done when `godot.build` is ok and
`grep -nE '#[0-9a-fA-F]{6}|Color\(|font_size|theme_override' scenes/ui/*.tscn` finds nothing.

## 3. Screenshot

`godot.screenshot(scene, width, height, state, hover)` once per mockup state, at the mockup frame size.
`hover` takes a Control path from the scene root, for states that show a hovered element.
It writes `.godot/screenshots/<scene>_<state>.png` and `.layout.json` (rect of every visible Control).

Done when every state has a PNG with `ok: true`. `environment_errors` (drivers, display) don't count.

## 4. Compare

Three passes, each against the mockup, each producing rows of one table
(element / property / mockup / fact / Δ / expected?):

1. **Geometry**: `uv run --script tools/design/figcraft.py diff design/<name>.figcraft <Frame>
   .godot/screenshots/<scene>_<state>.layout.json design/<name>.map.json`. Tolerance ±2px.
2. **Values**: each colour, font size, radius, border and margin in `theme.tres` against the table from
   step 1. Exact match.
3. **Picture**: read the screenshot and the mockup PNG side by side. Look for what numbers miss:
   wrong state, missing icon, text overflow, z-order, contrast against the live background.

Done when every layer from `map.json` has a geometry row and every theme value has a value row.

## 5. Fix

Fix the rows that are not expected mismatches, then repeat steps 3–4. At most **3 iterations**; what is
left after the third goes into the report.

## 6. Report

Three lists: **matches**, **mismatches** (with Δ, and why each is left, e.g. expected), **needs a human**
(animation, hover feel, blur, readability over the moving background). Give PNG paths for each iteration.
