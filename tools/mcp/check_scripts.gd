# Compiles every project GDScript (skipping addons/, .godot/ and this tool) with autoloads available.
# Usage: godot --headless --path . -s res://tools/mcp/check_scripts.gd
# Exit code 1 if any script fails to compile; engine prints the errors with res:// paths.
extends SceneTree

const SKIP: Array[String] = ["res://addons", "res://.godot", "res://tools/mcp"]


func _initialize() -> void:
	var failed := 0
	var checked := 0
	for path: String in _collect("res://"):
		checked += 1
		# Fresh process, so the default cache is fine; CACHE_MODE_IGNORE on already-loaded
		# scripts (autoloads) can crash the engine.
		var script := load(path) as GDScript
		# Godot 4.7 still returns a GDScript for a script that doesn't parse; it can't be instantiated.
		if script == null or not script.can_instantiate():
			failed += 1
			printerr("CHECK FAILED: %s" % path)
	print("CHECKED %d scripts, %d failed" % [checked, failed])
	quit(1 if failed else 0)


func _collect(dir_path: String) -> PackedStringArray:
	var out := PackedStringArray()
	if dir_path.trim_suffix("/") in SKIP:
		return out
	for file: String in DirAccess.get_files_at(dir_path):
		if file.get_extension() == "gd":
			out.append(dir_path.path_join(file))
	for sub: String in DirAccess.get_directories_at(dir_path):
		if not sub.begins_with("."):
			out.append_array(_collect(dir_path.path_join(sub)))
	return out
