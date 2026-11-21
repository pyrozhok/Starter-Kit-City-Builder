extends Node3D
## Root of the game scene. Opens the main menu over the sample city and connects menu,
## notifications, builder and camera; none of them knows about the others.

const MAP_SAVED := "Map saved"
const MAP_LOADED := "Map loaded"

@export var builder: Builder
@export var view: View
@export var menu: MainMenu
@export var hud: CanvasLayer
@export var notifications: Notifications


func _ready() -> void:
	builder.map_saved.connect(_on_map_saved)
	builder.map_loaded.connect(notifications.push.bind(MAP_LOADED))
	menu.new_game.connect(_start.bind(builder.new_map))
	menu.continue_game.connect(_start.bind(_load_save))
	menu.load_game.connect(_start.bind(_load_save))
	menu.exit_requested.connect(get_tree().quit)
	open_menu()


## Menu over the sample city: camera orbits, building and camera controls are off.
func open_menu() -> void:
	builder.load_map(Builder.SAMPLE_PATH, false)
	menu.has_save = FileAccess.file_exists(builder.save_path)
	_set_playing(false)


## Mockup states for godot.screenshot: "save" (design/main_menu.png), "nosave" (main_menu_nosave.png).
func _preview_state(state: String) -> void:
	menu.has_save = state == "save"
	notifications.push(MAP_LOADED)
	notifications.mark_all_read()
	notifications.push(MAP_SAVED)


func _start(prepare: Callable) -> void:
	prepare.call()
	_set_playing(true)
	view.reset()


## Playing: HUD, building and camera controls on, menu closed. Off: the menu over an orbiting city.
func _set_playing(on: bool) -> void:
	if on:
		menu.close()
	else:
		menu.open()
	hud.visible = on
	notifications.auto_hide = on
	builder.set_active(on)
	view.input_enabled = on
	view.auto_orbit = not on


func _load_save() -> void:
	builder.load_map(builder.save_path)


func _on_map_saved() -> void:
	notifications.push(MAP_SAVED)
	menu.has_save = true
