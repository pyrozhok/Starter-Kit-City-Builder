extends Node3D
## Root of the game scene. Opens the main menu over the sample city and connects menu,
## notifications, builder and camera; none of them knows about the others.

const MAP_SAVED := "Map saved"
const MAP_LOADED := "Map loaded"
const CREDITS_SOON := "Credits — coming soon"

@export var builder: Builder
@export var view: View
@export var menu: MainMenu
@export var options: OptionsMenu
@export var hud: CanvasLayer
@export var notifications: Notifications

## Where settings load from on start and save to on each finished change (tests point it elsewhere).
var settings_path := Settings.PATH

var _settings: Settings
var _base_orbit_speed: float


func _ready() -> void:
	_base_orbit_speed = view.orbit_speed
	_settings = Settings.load_from(settings_path)
	_apply_settings()
	options.settings = _settings
	options.settings_changed.connect(_apply_settings)
	options.settings_committed.connect(_on_settings_committed)
	options.back_requested.connect(_close_options)
	builder.map_saved.connect(_on_map_saved)
	builder.map_loaded.connect(notifications.push.bind(MAP_LOADED))
	menu.new_game.connect(_start.bind(builder.new_map))
	menu.continue_game.connect(_start.bind(_load_save))
	menu.load_game.connect(_start.bind(_load_save))
	menu.options_requested.connect(_open_options)
	menu.credits_requested.connect(notifications.push.bind(CREDITS_SOON))
	menu.exit_requested.connect(get_tree().quit)
	open_menu()


## Menu over the sample city: camera orbits, building and camera controls are off.
func open_menu() -> void:
	builder.load_map(Builder.SAMPLE_PATH, false)
	menu.has_save = FileAccess.file_exists(builder.save_path)
	_set_playing(false)


## Mockup states for godot.screenshot: "save" (design/main_menu.png), "nosave" (main_menu_nosave.png),
## and OptionsMenu's "options" / "options_drag" (design/options*.png), which change no setting.
func _preview_state(state: String) -> void:
	if state.begins_with("options"):
		_open_options()
		options._preview_state(state)
		return
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
	options.close()
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


## Options stand in for the menu; the city keeps orbiting behind them.
func _open_options() -> void:
	menu.close()
	options.open()


func _close_options() -> void:
	options.close()
	menu.open()


func _on_settings_committed() -> void:
	_settings.save(settings_path)


## Master bus covers the Audio autoload and the ambience player. The window mode is set only when
## it differs, so a windowed setting doesn't undo a maximized window.
func _apply_settings() -> void:
	AudioServer.set_bus_volume_linear(0, _settings.volume)
	view.orbit_speed = _base_orbit_speed * _settings.orbit_speed
	var mode := DisplayServer.window_get_mode()
	var is_fullscreen := mode == DisplayServer.WINDOW_MODE_FULLSCREEN \
			or mode == DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN
	if _settings.fullscreen != is_fullscreen:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN if _settings.fullscreen
				else DisplayServer.WINDOW_MODE_WINDOWED)


func _on_map_saved() -> void:
	notifications.push(MAP_SAVED)
	menu.has_save = true
