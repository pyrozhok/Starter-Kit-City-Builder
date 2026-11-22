extends GutTest
## Mockup component "Slider" from design/options.figcraft.

func _instance(path: String) -> Control:
	var node := (load(path) as PackedScene).instantiate() as Control
	node.theme = load("res://scenes/ui/theme.tres")  # in the game it comes from the menu's Root
	add_child_autofree(node)
	return node


func test_slider_looks_pressed_only_while_dragged() -> void:
	var slider := _instance("res://scenes/ui/option_slider.tscn") as OptionSlider
	assert_eq(slider.theme_type_variation, &"OptionSlider")
	slider.drag_started.emit()
	assert_eq(slider.theme_type_variation, &"OptionSliderPressed")
	slider.drag_ended.emit(true)
	assert_eq(slider.theme_type_variation, &"OptionSlider")
