extends CheckButton
## Mockup component "Toggle". CheckButton has no hover icons, so Hover is its own variation.


func _ready() -> void:
	mouse_entered.connect(func() -> void: theme_type_variation = &"OptionToggleHover")
	mouse_exited.connect(func() -> void: theme_type_variation = &"OptionToggle")
