extends GutTest

const SAVE_PATH := "user://test_main_map.res"
const SETTINGS_PATH := "user://test_main_settings.cfg"
const Main := preload("res://scripts/main.gd")

var main: Node3D
var builder: Builder
var view: View
var menu: MainMenu
var notifications: Notifications
var options: OptionsMenu
## The fullscreen toggle sets the real window mode; after_each puts this one back.
var window_mode: DisplayServer.WindowMode


func before_each() -> void:
	window_mode = DisplayServer.window_get_mode()
	main = (load("res://scenes/main.tscn") as PackedScene).instantiate()
	builder = main.get_node("Builder")
	builder.save_path = SAVE_PATH  # before _ready: main checks it when it opens the menu
	view = main.get_node("View")
	menu = main.get_node("MainMenu")
	notifications = main.get_node("Overlay/Notifications")
	options = main.get_node("OptionsMenu")
	main.settings_path = SETTINGS_PATH  # before _ready: main loads it on start


func after_each() -> void:
	Input.action_release("build")
	for path: String in [SAVE_PATH, SETTINGS_PATH]:
		if FileAccess.file_exists(path):
			DirAccess.remove_absolute(path)
	AudioServer.set_bus_volume_linear(0, 1.0)
	if DisplayServer.window_get_mode() != window_mode:
		DisplayServer.window_set_mode(window_mode)


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


func test_start_resets_the_orbited_camera_angle() -> void:
	_start()
	var home: Vector3 = view.camera_rotation
	view.camera_rotation.y += 100.0  # the menu orbit
	menu.new_game.emit()
	assert_almost_eq(fposmod(view.camera_rotation.y - home.y, 360.0), 0.0, 0.001)


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
	assert_eq(notifications.items()[0].text, Main.MAP_LOADED)


func test_save_notifies_and_enables_continue() -> void:
	_start()
	builder.map_saved.emit()
	assert_eq(notifications.items()[0].text, Main.MAP_SAVED)
	assert_true(notifications.items()[0].unread)
	assert_true(menu.has_save)


func _move_mouse(viewport: SubViewport, position: Vector2) -> void:
	var motion := InputEventMouseMotion.new()
	motion.position = position
	motion.global_position = position
	viewport.push_input(motion)


func test_notifications_hide_while_playing_and_free_the_corner() -> void:
	var viewport := SubViewport.new()  # own viewport: GUT's panel can't be the hovered Control
	viewport.size = Vector2i(1920, 1080)
	add_child_autofree(viewport)
	notifications.hide_delay = 0.3  # above the first frames' load time
	viewport.add_child(main)
	menu.new_game.emit()
	await wait_process_frames(2)
	builder.map_saved.emit()
	await wait_process_frames(2)  # container layout
	var corner := notifications.get_global_rect().get_center()
	_move_mouse(viewport, corner)
	assert_true(builder.pointer_over_ui(), "precondition: the panel covers the corner")
	await wait_seconds(0.5)
	assert_true(notifications.visible, "stays while the pointer is over it")
	_move_mouse(viewport, Vector2(960, 300))
	await wait_seconds(0.5)
	assert_false(notifications.visible, "hides after the delay")
	_move_mouse(viewport, corner)
	assert_false(builder.pointer_over_ui())
	await wait_process_frames(1)  # wait_seconds resumes in a physics frame, where just_pressed is false
	Input.action_press("build")
	builder.action_build(Vector3(2, 0, 3))
	assert_ne(builder.gridmap.get_cell_item(Vector3i(2, 0, 3)), GridMap.INVALID_CELL_ITEM, "building works again")


func test_notifications_stay_in_the_menu() -> void:
	notifications.hide_delay = 0.05
	_start()
	builder.map_saved.emit()
	await wait_seconds(0.1)
	assert_true(notifications.visible)


func test_credits_say_coming_soon() -> void:
	_start()
	menu.credits_requested.emit()
	assert_eq(notifications.items()[0].text, Main.CREDITS_SOON)
	assert_true(notifications.visible)


func test_options_replace_the_menu_and_back_returns() -> void:
	_start()
	assert_false(options.visible, "closed on start")
	menu.options_requested.emit()
	assert_true(options.visible)
	assert_false(menu.visible)
	assert_true(view.auto_orbit, "city keeps orbiting behind the options")
	options.back_requested.emit()
	assert_false(options.visible)
	assert_true(menu.visible)


func test_start_applies_saved_settings() -> void:
	var saved := Settings.new()
	saved.volume = 0.5
	saved.orbit_speed = 2.0
	saved.save(SETTINGS_PATH)
	var base_speed := view.orbit_speed
	_start()
	assert_almost_eq(AudioServer.get_bus_volume_linear(0), 0.5, 0.001)
	assert_almost_eq(view.orbit_speed, base_speed * 2.0, 0.001)
	assert_almost_eq(options.settings.volume, 0.5, 0.001, "options show what was loaded")


func test_changed_settings_are_applied_and_saved() -> void:
	var base_speed := view.orbit_speed
	_start()
	options.settings.volume = 0.25
	options.settings.orbit_speed = 0.5
	options.settings_changed.emit()
	options.settings_committed.emit()
	assert_almost_eq(AudioServer.get_bus_volume_linear(0), 0.25, 0.001)
	assert_almost_eq(view.orbit_speed, base_speed * 0.5, 0.001)
	var saved := Settings.load_from(SETTINGS_PATH)
	assert_almost_eq(saved.volume, 0.25, 0.001)
	assert_almost_eq(saved.orbit_speed, 0.5, 0.001)


func test_slider_ticks_apply_live_and_save_when_the_drag_ends() -> void:
	_start()
	var slider := options.get_node(OptionsMenu.ROWS + "MasterVolume/Box/VolumeSlider") as OptionSlider
	slider.drag_started.emit()
	slider.value = 30.0
	assert_almost_eq(AudioServer.get_bus_volume_linear(0), 0.3, 0.001)
	assert_false(FileAccess.file_exists(SETTINGS_PATH), "a tick does not write the file")
	slider.drag_ended.emit(true)
	assert_almost_eq(Settings.load_from(SETTINGS_PATH).volume, 0.3, 0.001)


func test_toggle_and_back_save_settings() -> void:
	_start()
	var toggle := options.get_node(OptionsMenu.ROWS + "DisplayMode/Box/FullscreenToggle") as CheckButton
	toggle.button_pressed = true
	assert_true(Settings.load_from(SETTINGS_PATH).fullscreen)
	toggle.set_pressed_no_signal(false)
	options.settings.fullscreen = false
	DirAccess.remove_absolute(SETTINGS_PATH)
	(options.get_node(OptionsMenu.ROWS + "Footer/Box/BackButton") as Button).pressed.emit()
	assert_true(FileAccess.file_exists(SETTINGS_PATH), "back saves")
