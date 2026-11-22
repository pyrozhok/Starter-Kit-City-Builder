extends Button
## Mockup component "MenuButton". With a key (prop ShowKey), a Keycap stands where the icon would,
## one h_separation before the text; MainMenuButtonKeyed makes room for it.

const STYLES: Dictionary[BaseButton.DrawMode, StringName] = {
	DRAW_NORMAL: &"normal", DRAW_HOVER: &"hover", DRAW_PRESSED: &"pressed",
	DRAW_HOVER_PRESSED: &"hover_pressed", DRAW_DISABLED: &"disabled",
}

## Key shown on the keycap, e.g. "ESC"; empty hides it.
@export var key := "":
	set(value):
		key = value
		if is_node_ready():
			_show_key()

@onready var _keycap: Control = $Keycap


func _ready() -> void:
	_show_key()
	draw.connect(_place_keycap)


func _show_key() -> void:
	_keycap.visible = not key.is_empty()
	(_keycap.get_node("Key") as Label).text = key
	theme_type_variation = &"MainMenuButton" if key.is_empty() else &"MainMenuButtonKeyed"


## The text start moves with the state's stylebox (hover adds the left border); the keycap follows.
func _place_keycap() -> void:
	if not _keycap.visible:
		return
	var text_left := get_theme_stylebox(STYLES[get_draw_mode()]).get_margin(SIDE_LEFT)
	var width := _keycap.get_combined_minimum_size().x
	_keycap.position.x = text_left - get_theme_constant(&"h_separation") - width
