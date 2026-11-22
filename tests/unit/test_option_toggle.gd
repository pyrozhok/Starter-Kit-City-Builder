extends GutTest
## Mockup component "Toggle" from design/options.figcraft.

func _instance(path: String) -> Control:
	var node := (load(path) as PackedScene).instantiate() as Control
	node.theme = load("res://scenes/ui/theme.tres")  # in the game it comes from the menu's Root
	add_child_autofree(node)
	return node


func test_toggle_looks_hovered_only_under_the_mouse() -> void:
	var toggle := _instance("res://scenes/ui/option_toggle.tscn") as CheckButton
	assert_eq(toggle.theme_type_variation, &"OptionToggle")
	toggle.mouse_entered.emit()
	assert_eq(toggle.theme_type_variation, &"OptionToggleHover")
	toggle.mouse_exited.emit()
	assert_eq(toggle.theme_type_variation, &"OptionToggle")
