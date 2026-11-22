extends GutTest

const ROWS := "Root/Panel/Box/Content/"

var options: OptionsMenu


func before_each() -> void:
	options = (load("res://scenes/ui/options_menu.tscn") as PackedScene).instantiate()
	add_child_autofree(options)


func _node(path: String) -> Node:
	return options.get_node(ROWS + path)


func _settings(volume: float, fullscreen: bool, orbit_speed: float) -> Settings:
	var settings := Settings.new()
	settings.volume = volume
	settings.fullscreen = fullscreen
	settings.orbit_speed = orbit_speed
	return settings


func _cancel() -> InputEventAction:
	var event := InputEventAction.new()
	event.action = &"ui_cancel"
	event.pressed = true
	return event


func test_shows_the_settings_it_is_given() -> void:
	options.settings = _settings(0.7, true, 0.5)
	assert_eq((_node("MasterVolume/Box/VolumeSlider") as Range).value, 70.0)
	assert_eq((_node("MasterVolume/Box/Value") as Label).text, "70%")
	assert_true((_node("DisplayMode/Box/FullscreenToggle") as Button).button_pressed)
	assert_eq((_node("DisplayMode/Box/Value") as Label).text, "FULLSCREEN")
	assert_eq((_node("CameraOrbitSpeed/Box/OrbitSpeedSlider") as Range).value, 0.5)
	assert_eq((_node("CameraOrbitSpeed/Box/Value") as Label).text, "0.5×")


func test_showing_settings_is_not_a_change() -> void:
	watch_signals(options)
	options.settings = _settings(0.7, true, 0.5)
	assert_signal_not_emitted(options, "settings_changed")


func test_slider_ranges_follow_the_spec() -> void:
	var volume := _node("MasterVolume/Box/VolumeSlider") as Range
	assert_eq([volume.min_value, volume.max_value, volume.step], [0.0, 100.0, 5.0])
	var orbit := _node("CameraOrbitSpeed/Box/OrbitSpeedSlider") as Range
	assert_eq([orbit.min_value, orbit.max_value, orbit.step], [0.0, Settings.ORBIT_SPEED_MAX, 0.1])


func test_volume_slider_edits_settings() -> void:
	watch_signals(options)
	(_node("MasterVolume/Box/VolumeSlider") as Range).value = 40.0
	assert_almost_eq(options.settings.volume, 0.4, 0.0001)
	assert_eq((_node("MasterVolume/Box/Value") as Label).text, "40%")
	assert_signal_emitted(options, "settings_changed")


func test_fullscreen_toggle_edits_settings() -> void:
	watch_signals(options)
	var toggle := _node("DisplayMode/Box/FullscreenToggle") as Button
	toggle.button_pressed = true
	assert_true(options.settings.fullscreen)
	assert_eq((_node("DisplayMode/Box/Value") as Label).text, "FULLSCREEN")
	toggle.button_pressed = false
	assert_false(options.settings.fullscreen)
	assert_eq((_node("DisplayMode/Box/Value") as Label).text, "WINDOWED")
	assert_signal_emit_count(options, "settings_changed", 2)


func test_orbit_slider_edits_settings() -> void:
	watch_signals(options)
	(_node("CameraOrbitSpeed/Box/OrbitSpeedSlider") as Range).value = 1.5
	assert_almost_eq(options.settings.orbit_speed, 1.5, 0.0001)
	assert_eq((_node("CameraOrbitSpeed/Box/Value") as Label).text, "1.5×")
	assert_signal_emitted(options, "settings_changed")


func test_back_button_asks_to_go_back() -> void:
	watch_signals(options)
	(_node("Footer/Box/BackButton") as Button).pressed.emit()
	assert_signal_emitted(options, "back_requested")


func test_cancel_goes_back_only_while_open() -> void:
	watch_signals(options)
	options.close()
	options._unhandled_input(_cancel())
	assert_signal_not_emitted(options, "back_requested")
	options.open()
	options._unhandled_input(_cancel())
	assert_signal_emitted(options, "back_requested")


func test_preview_keeps_editing_the_given_settings() -> void:
	var given := _settings(1.0, false, 1.0)
	options.settings = given
	watch_signals(options)
	options._preview_state("options")
	assert_signal_not_emitted(options, "settings_changed")
	assert_eq((_node("MasterVolume/Box/Value") as Label).text, "70%")
	(_node("MasterVolume/Box/VolumeSlider") as Range).value = 40.0
	assert_almost_eq(given.volume, 0.4, 0.0001)


func test_slider_change_outside_a_drag_is_committed() -> void:
	watch_signals(options)
	(_node("MasterVolume/Box/VolumeSlider") as Range).value = 40.0
	(_node("CameraOrbitSpeed/Box/OrbitSpeedSlider") as Range).value = 1.5
	assert_signal_emit_count(options, "settings_committed", 2)


func test_slider_change_during_a_drag_is_committed_when_the_drag_ends() -> void:
	watch_signals(options)
	var commits := 0
	for path: String in ["MasterVolume/Box/VolumeSlider", "CameraOrbitSpeed/Box/OrbitSpeedSlider"]:
		var slider := _node(path) as OptionSlider
		slider.drag_started.emit()
		slider.value = 1.0
		assert_signal_emit_count(options, "settings_committed", commits, path + " mid-drag")
		slider.drag_ended.emit(true)
		commits += 1
		assert_signal_emit_count(options, "settings_committed", commits, path + " drag end")


func test_volume_label_agrees_with_the_slider_off_its_step() -> void:
	options.settings = _settings(0.33, false, 1.0)
	assert_eq((_node("MasterVolume/Box/VolumeSlider") as Range).value, 35.0)
	assert_eq((_node("MasterVolume/Box/Value") as Label).text, "35%")
