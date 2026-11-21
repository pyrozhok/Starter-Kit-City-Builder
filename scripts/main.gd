extends Node3D
## Root of the game scene. Opens the main menu over the sample city and connects menu,
## notifications, builder and camera; none of them knows about the others.

@export var builder: Builder
@export var view: View
@export var menu: MainMenu
@export var hud: CanvasLayer
@export var notifications: Notifications


func _ready() -> void:
	builder.map_saved.connect(_on_map_saved)
	builder.map_loaded.connect(notifications.push.bind("Map loaded"))
	menu.new_game.connect(_start.bind(builder.new_map))
	menu.continue_game.connect(_start.bind(_load_save))
	menu.load_game.connect(_start.bind(_load_save))
	menu.exit_requested.connect(get_tree().quit)
	open_menu()


## Menu over the sample city: camera orbits, building and camera controls are off.
func open_menu() -> void:
	builder.load_map(Builder.SAMPLE_PATH, false)
	builder.set_active(false)
	view.input_enabled = false
	view.auto_orbit = true
	hud.hide()
	menu.has_save = FileAccess.file_exists(builder.save_path)
	menu.open()


## Mockup states for godot.screenshot: "save" (design/main_menu.png), "nosave" (main_menu_nosave.png).
func _preview_state(state: String) -> void:
	menu.has_save = state == "save"
	notifications.push("Map loaded")
	notifications.mark_all_read()
	notifications.push("Map saved")


func _start(prepare: Callable) -> void:
	prepare.call()
	menu.close()
	hud.show()
	builder.set_active(true)
	view.input_enabled = true
	view.auto_orbit = false
	view.camera_position = Vector3.ZERO


func _load_save() -> void:
	builder.load_map(builder.save_path)


func _on_map_saved() -> void:
	notifications.push("Map saved")
	menu.has_save = true
