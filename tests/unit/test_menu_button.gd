extends GutTest
## Mockup component "MenuButton" with a keycap, from design/options.figcraft.

func _instance(path: String) -> Control:
	var node := (load(path) as PackedScene).instantiate() as Control
	node.theme = load("res://scenes/ui/theme.tres")  # in the game it comes from the menu's Root
	add_child_autofree(node)
	return node


func test_menu_button_without_key_hides_keycap() -> void:
	var button := _instance("res://scenes/ui/menu_button.tscn") as Button
	assert_false(button.get_node("Keycap").visible)
	assert_eq(button.theme_type_variation, &"MainMenuButton")


func test_menu_button_key_shows_keycap_left_of_text() -> void:
	var button := _instance("res://scenes/ui/menu_button.tscn") as Button
	button.set("key", "ESC")
	button.size = Vector2(260, 64)
	await wait_process_frames(2)
	var keycap := button.get_node("Keycap") as Control
	assert_true(keycap.visible)
	assert_eq(button.theme_type_variation, &"MainMenuButtonKeyed")
	assert_eq((keycap.get_node("Key") as Label).text, "ESC")
	var text_left := button.get_theme_stylebox(&"normal").get_margin(SIDE_LEFT)
	var gap := button.get_theme_constant(&"h_separation")
	assert_eq(keycap.position.x + keycap.size.x + gap, text_left, "keycap ends one gap before the text")
