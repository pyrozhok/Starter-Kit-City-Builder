class_name OptionsMenu
extends CanvasLayer
## Mockup frame "Options". Shows a Settings and edits it in place; holds no game state: whoever
## owns the game gives it the settings, applies them on settings_changed, saves them on
## settings_committed, and closes it on back_requested.

## Every edit, slider ticks included.
signal settings_changed
## A finished edit: a slider drag ends, a slider moves outside a drag (wheel, keys), a toggle
## flips, or the menu goes back.
signal settings_committed
signal back_requested

const ROWS := "Root/Panel/Box/Content/"
const VOLUME_FORMAT := "%d%%"
const ORBIT_FORMAT := "%.1f×"
const FULLSCREEN_TEXT := "FULLSCREEN"
const WINDOWED_TEXT := "WINDOWED"

## Shown without emitting settings_changed; the controls then edit this object.
var settings := Settings.new():
	set(value):
		settings = value
		if is_node_ready():
			_show()

@onready var _volume: OptionSlider = get_node(ROWS + "MasterVolume/Box/VolumeSlider")
@onready var _volume_value: Label = get_node(ROWS + "MasterVolume/Box/Value")
@onready var _fullscreen: CheckButton = get_node(ROWS + "DisplayMode/Box/FullscreenToggle")
@onready var _fullscreen_value: Label = get_node(ROWS + "DisplayMode/Box/Value")
@onready var _orbit: OptionSlider = get_node(ROWS + "CameraOrbitSpeed/Box/OrbitSpeedSlider")
@onready var _orbit_value: Label = get_node(ROWS + "CameraOrbitSpeed/Box/Value")


func _ready() -> void:
	_orbit.max_value = Settings.ORBIT_SPEED_MAX
	_show()
	_volume.value_changed.connect(_on_volume_changed)
	_fullscreen.toggled.connect(_on_fullscreen_toggled)
	_orbit.value_changed.connect(_on_orbit_changed)
	_volume.drag_ended.connect(_on_drag_ended)
	_orbit.drag_ended.connect(_on_drag_ended)
	(get_node(ROWS + "Footer/Box/BackButton") as Button).pressed.connect(_back)


func _unhandled_input(event: InputEvent) -> void:
	if visible and event.is_action_pressed(&"ui_cancel"):
		get_viewport().set_input_as_handled()
		_back()


func open() -> void:
	show()


func close() -> void:
	hide()


## Mockup states for godot.screenshot: "options" (design/options.png) and "options_drag"
## (options_hover.png, with hover on the Back button). Values go into the given settings without a
## signal, so nothing is applied or saved and the controls keep editing the owner's object.
func _preview_state(state: String) -> void:
	settings.volume = 0.85 if state == "options_drag" else 0.7
	settings.fullscreen = true
	settings.orbit_speed = 0.5
	_show()
	_volume.dragging = state == "options_drag"


func _show() -> void:
	_volume.set_value_no_signal(settings.volume * 100.0)
	_fullscreen.set_pressed_no_signal(settings.fullscreen)
	_orbit.set_value_no_signal(settings.orbit_speed)
	_update_labels()


func _update_labels() -> void:
	_volume_value.text = VOLUME_FORMAT % roundi(settings.volume * 100.0)
	_fullscreen_value.text = FULLSCREEN_TEXT if settings.fullscreen else WINDOWED_TEXT
	_orbit_value.text = ORBIT_FORMAT % settings.orbit_speed


func _on_volume_changed(value: float) -> void:
	settings.volume = value / 100.0
	_changed()
	_commit_unless_dragging(_volume)


func _on_fullscreen_toggled(on: bool) -> void:
	settings.fullscreen = on
	_changed()
	settings_committed.emit()


func _on_orbit_changed(value: float) -> void:
	settings.orbit_speed = value
	_changed()
	_commit_unless_dragging(_orbit)


func _changed() -> void:
	_update_labels()
	settings_changed.emit()


## A drag commits once, when it ends.
func _commit_unless_dragging(slider: OptionSlider) -> void:
	if not slider.dragging:
		settings_committed.emit()


func _on_drag_ended(_value_changed: bool) -> void:
	settings_committed.emit()


func _back() -> void:
	settings_committed.emit()
	back_requested.emit()
