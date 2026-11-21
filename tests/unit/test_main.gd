extends GutTest

const SAVE_PATH := "user://test_main_map.res"

var main: Node3D
var builder: Builder
var view: View
var menu: MainMenu
var notifications: Notifications


func before_each() -> void:
	main = (load("res://scenes/main.tscn") as PackedScene).instantiate()
	builder = main.get_node("Builder")
	builder.save_path = SAVE_PATH  # before _ready: main checks it when it opens the menu
	view = main.get_node("View")
	menu = main.get_node("MainMenu")
	notifications = main.get_node("Overlay/Notifications")


func after_each() -> void:
	if FileAccess.file_exists(SAVE_PATH):
		DirAccess.remove_absolute(SAVE_PATH)


func _start() -> void:
	add_child_autofree(main)


func test_opens_menu_over_sample_city_with_controls_off() -> void:
	_start()
	assert_true(menu.visible)
	assert_false(builder.is_processing())
	assert_false(view.input_enabled)
	assert_true(view.auto_orbit)
	assert_gt(builder.gridmap.get_used_cells().size(), 0, "sample map loaded as background")
	assert_eq(notifications.items().size(), 0, "background load is not announced")


func test_menu_disables_continue_without_save() -> void:
	_start()
	assert_false(menu.has_save)


func test_menu_enables_continue_with_save() -> void:
	ResourceSaver.save(DataMap.new(), SAVE_PATH)
	_start()
	assert_true(menu.has_save)


func test_new_game_starts_empty_map_with_controls_on() -> void:
	_start()
	menu.new_game.emit()
	assert_false(menu.visible)
	assert_true(builder.is_processing())
	assert_true(view.input_enabled)
	assert_false(view.auto_orbit)
	assert_eq(builder.gridmap.get_used_cells().size(), 0)


func test_continue_loads_save_and_announces_it() -> void:
	var map := DataMap.new()
	var cell := DataStructure.new()
	cell.position = Vector2i(7, 7)
	map.structures.append(cell)
	ResourceSaver.save(map, SAVE_PATH)
	_start()
	menu.continue_game.emit()
	assert_false(menu.visible)
	assert_eq(builder.gridmap.get_used_cells(), [Vector3i(7, 0, 7)])
	assert_eq(notifications.items()[0].text, "Map loaded")


func test_save_notifies_and_enables_continue() -> void:
	_start()
	builder.map_saved.emit()
	assert_eq(notifications.items()[0].text, "Map saved")
	assert_true(notifications.items()[0].unread)
	assert_true(menu.has_save)
