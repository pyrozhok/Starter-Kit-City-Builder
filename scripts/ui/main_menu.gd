class_name MainMenu
extends CanvasLayer
## Mockup frame "MainMenu". Reports what the player picked through signals and holds no game
## state: whoever owns the game connects the signals and sets has_save.

signal new_game
signal continue_game
signal load_game
signal options_requested
signal credits_requested
signal exit_requested

const TIP_TITLE := "%s / %s — switch building"
const TIP_BODY := "%s rotate · %s demolish"
const MOUSE_NAMES := {MOUSE_BUTTON_LEFT: "LMB", MOUSE_BUTTON_RIGHT: "RMB", MOUSE_BUTTON_MIDDLE: "MMB"}

## Continue and Load are enabled only when there is a save to load.
var has_save := false:
	set(value):
		has_save = value
		if is_node_ready():
			_continue.disabled = not value
			_load.disabled = not value

@onready var _continue: Button = %Continue
@onready var _load: Button = %Load


func _ready() -> void:
	has_save = has_save
	_continue.pressed.connect(continue_game.emit)
	%NewGame.pressed.connect(new_game.emit)
	_load.pressed.connect(load_game.emit)
	%Options.pressed.connect(options_requested.emit)
	%Credits.pressed.connect(credits_requested.emit)
	%Exit.pressed.connect(exit_requested.emit)
	%TipTitle.text = TIP_TITLE % [binding_text(&"structure_previous"), binding_text(&"structure_next")]
	%TipBody.text = TIP_BODY % [binding_text(&"rotate"), binding_text(&"demolish")]


func open() -> void:
	show()


func close() -> void:
	hide()


## First binding of an input action as the player would name it: "Q", "Delete", "RMB".
static func binding_text(action: StringName) -> String:
	for event: InputEvent in InputMap.action_get_events(action):
		var key := event as InputEventKey
		if key:
			return OS.get_keycode_string(key.physical_keycode if key.physical_keycode else key.keycode)
		var mouse := event as InputEventMouseButton
		if mouse:
			return MOUSE_NAMES.get(mouse.button_index, "Mouse %d" % mouse.button_index)
	return "?"
