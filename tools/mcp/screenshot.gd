# Renders one scene into an exact-size SubViewport and saves a PNG plus a layout dump.
# Usage (windowed, not --headless: headless has no renderer):
#   godot --path . -s res://tools/mcp/screenshot.gd -- --scene=res://scenes/main.tscn \
#     --out=/abs/path.png [--size=1920x1080] [--state=name] [--hover=Node/Path] [--frames=30]
# The SubViewport, not the window, sets the size, so window managers that resize windows
# (tiling) don't change the result. --state calls `_preview_state(state)` on the scene root if it
# has one. --hover sends a mouse motion to the centre of that Control (path from the scene root).
# Writes <out>.png and <out>.layout.json ({size, blank, controls: [{path, type, variation, x, y, w, h}]}),
# prints "SCREENSHOT <path>" and exits 0, or prints "SCREENSHOT FAILED: ..." and exits 1.
extends SceneTree

const BLANK_SAMPLES := 48  # grid of BLANK_SAMPLES² pixels checked for "all one colour"


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var args := _parse_args()
	var scene_path: String = args.get("scene", "")
	var out_path: String = args.get("out", "")
	if scene_path.is_empty() or out_path.is_empty():
		_fail("--scene and --out are required")
		return
	var packed := load(scene_path) as PackedScene
	if packed == null:
		_fail("cannot load scene %s" % scene_path)
		return
	var size_parts: PackedStringArray = String(args.get("size", "1920x1080")).split("x")
	var size := Vector2i(int(size_parts[0]), int(size_parts[1]))

	var sub := SubViewport.new()
	sub.size = size
	sub.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(sub)
	var scene := packed.instantiate()
	sub.add_child(scene)

	var state: String = args.get("state", "")
	if not state.is_empty():
		if not scene.has_method("_preview_state"):
			_fail("state '%s' given but %s has no _preview_state()" % [state, scene_path])
			return
		scene.call("_preview_state", state)

	var frames := int(args.get("frames", "30"))
	for i in frames:
		await process_frame

	var hover: String = args.get("hover", "")
	if not hover.is_empty():
		var target := scene.get_node_or_null(hover) as Control
		if target == null:
			_fail("hover target not found or not a Control: %s" % hover)
			return
		var motion := InputEventMouseMotion.new()
		motion.position = _canvas_rect(target).get_center()
		motion.global_position = motion.position
		sub.push_input(motion)
		for i in 10:  # let hover styles and tweens settle
			await process_frame

	await RenderingServer.frame_post_draw
	var image := sub.get_texture().get_image()
	var err := image.save_png(out_path)
	if err != OK:
		_fail("save_png(%s) failed: %s" % [out_path, error_string(err)])
		return
	var layout_path := out_path.get_basename() + ".layout.json"
	var layout := FileAccess.open(layout_path, FileAccess.WRITE)
	layout.store_string(JSON.stringify({"scene": scene_path, "state": state, "hover": hover,
		"size": [image.get_width(), image.get_height()], "blank": _is_blank(image),
		"controls": _layout(scene)}, "\t"))
	layout.close()
	sub.free()  # otherwise the scene's resources are reported as leaked at exit
	print("SCREENSHOT " + out_path)
	quit(0)


func _parse_args() -> Dictionary:
	var out := {}
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--") and "=" in arg:
			var kv := arg.trim_prefix("--").split("=", true, 1)
			out[kv[0]] = kv[1]
	return out


# Rect in viewport pixels, including CanvasLayer offsets/scale.
func _canvas_rect(control: Control) -> Rect2:
	var xf := control.get_global_transform_with_canvas()
	return Rect2(xf.origin, control.size * xf.get_scale())


# Every visible Control: path from the scene root, class, theme variation, rect in viewport pixels.
func _layout(scene: Node) -> Array:
	var out: Array = []
	var stack: Array[Node] = [scene]
	while not stack.is_empty():
		var node: Node = stack.pop_back()
		var children := node.get_children()
		children.reverse()
		stack.append_array(children)
		var control := node as Control
		if control == null or not control.is_visible_in_tree():
			continue
		var r := _canvas_rect(control)
		var entry := {"path": str(scene.get_path_to(control)), "type": control.get_class(),
			"variation": str(control.theme_type_variation), "x": r.position.x, "y": r.position.y,
			"w": r.size.x, "h": r.size.y}
		if control is Label or control is Button:
			entry["text"] = control.get("text")
		out.append(entry)
	return out


func _is_blank(image: Image) -> bool:
	var first := image.get_pixel(0, 0)
	for gy in BLANK_SAMPLES:
		for gx in BLANK_SAMPLES:
			var p := image.get_pixel(int(gx * (image.get_width() - 1) / float(BLANK_SAMPLES - 1)),
				int(gy * (image.get_height() - 1) / float(BLANK_SAMPLES - 1)))
			if not p.is_equal_approx(first):
				return false
	return true


func _fail(message: String) -> void:
	printerr("SCREENSHOT FAILED: " + message)
	quit(1)
