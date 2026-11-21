---
name: generate-ui
description: In-game UI for this city builder: HUD, menu, panel, button, popup, label. Use when adding, restyling or wiring up UI in scenes/*.tscn.
---

# Generate UI

Terms follow `GLOSSARY.md`.

## 1. Inspect

`godot.scene_tree` on `res://scenes/main.tscn` (or `godot.find_scenes` with a node/type/script name).
The HUD lives under `CanvasLayer`; read node paths, anchors and existing styling from there.
Done when you can name the parent node for the new UI and the style resource it will reuse.

## 2. Build

- Text style is shared, never copied: the sub_resource `LabelSettings_q176i` in `main.tscn`. When a
  second scene needs it, move it to a `.tres` (e.g. `scenes/ui/label_settings.tres`) and point both
  at that file.
- More than one node → its own scene `scenes/ui/<name>.tscn`: root `Control` / `PanelContainer` /
  `MarginContainer`, layout through containers and anchors; behavior in `scripts/ui/<name>.gd`
  (typed GDScript). Instance it under the right `CanvasLayer` child.
- Wiring, game → UI: `@export var <name>: <Type>` on the owning script, assigned through
  `node_paths=` in the scene (pattern: `cash_display` in `builder.gd`).
  UI → game: the UI script emits signals; the game connects to them.
- Every new input action goes into `project.godot` `[input]`, keyboard and mouse where both make sense.

Done when the scene parses (`godot.build` ok) and the node sits where step 1 said.

## Clicks pass through UI

`builder.gd` polls `Input.is_action_just_pressed("build" / "demolish")` in `_process`, which fires
whether or not a Control consumed the click: pressing a button also builds on the tile under it.
`mouse_filter` alone leaves this unsolved.

- Decorative Controls: `mouse_filter = MOUSE_FILTER_IGNORE`, so they never count as hovered.
- Interactive Controls: `MOUSE_FILTER_STOP`, plus a guard at the top of `action_build` and
  `action_demolish`: `if get_viewport().gui_get_hovered_control() != null: return`.
  That guard is a gameplay change: ask the user first, and cover it with `write-test`.

## Editing `.tscn` text

- New `[ext_resource ...]` gets a fresh unique `id` (e.g. `"30_hud"`) and no `uid=` — Godot assigns
  it on the next import. Existing ids and uids stay exactly as they are.
- `parent=` paths are relative to the root (`parent="CanvasLayer/Top"`); the root node has none.
- When resource counts change, drop `load_steps` from the header; Godot recomputes it.

## 3. Verify

- `godot.build`: `ok: true`, `files_changed_by_build` holds only files you meant to create.
- `godot.run_tests`: `ok: true`; UI with logic has a test (`write-test`).
- `godot.scene_tree` again shows the node at the intended path.

Then ask the user to check the layout in the editor or game — headless runs can't see it.
