extends GutTest

var menu: MainMenu


func before_each() -> void:
	menu = (load("res://scenes/ui/main_menu.tscn") as PackedScene).instantiate()
	add_child_autofree(menu)


func _button(name: String) -> Button:
	return menu.get_node("%" + name) as Button


func test_without_save_continue_and_load_are_disabled() -> void:
	menu.has_save = false
	assert_true(_button("Continue").disabled)
	assert_true(_button("Load").disabled)
	assert_false(_button("NewGame").disabled)


func test_with_save_continue_and_load_are_enabled() -> void:
	menu.has_save = true
	assert_false(_button("Continue").disabled)
	assert_false(_button("Load").disabled)


func test_buttons_emit_their_signals() -> void:
	watch_signals(menu)
	for pair: Array in [["Continue", "continue_game"], ["NewGame", "new_game"], ["Load", "load_game"],
			["Options", "options_requested"], ["Credits", "credits_requested"], ["Exit", "exit_requested"]]:
		_button(pair[0]).pressed.emit()
		assert_signal_emitted(menu, pair[1], pair[0])


func test_tip_shows_current_bindings() -> void:
	assert_eq(menu.get_node("%TipTitle").text, "Q / E — switch building")
	assert_eq(menu.get_node("%TipBody").text, "RMB rotate · Delete demolish")


func test_binding_text_follows_input_map() -> void:
	InputMap.add_action(&"test_action")
	var key := InputEventKey.new()
	key.physical_keycode = KEY_F5
	InputMap.action_add_event(&"test_action", key)
	assert_eq(MainMenu.binding_text(&"test_action"), "F5")
	InputMap.erase_action(&"test_action")
