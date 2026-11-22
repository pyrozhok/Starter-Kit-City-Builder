extends GutTest

const PATH := "user://test_settings.cfg"


func after_each() -> void:
	if FileAccess.file_exists(PATH):
		DirAccess.remove_absolute(PATH)


func test_missing_file_gives_defaults() -> void:
	var settings := Settings.load_from(PATH)
	assert_eq(settings.volume, 1.0)
	assert_false(settings.fullscreen)
	assert_eq(settings.orbit_speed, 1.0)


func test_round_trips_through_config_file() -> void:
	var settings := Settings.new()
	settings.volume = 0.35
	settings.fullscreen = true
	settings.orbit_speed = 1.7
	assert_eq(settings.save(PATH), OK)
	var loaded := Settings.load_from(PATH)
	assert_eq(loaded.volume, 0.35)
	assert_true(loaded.fullscreen)
	assert_eq(loaded.orbit_speed, 1.7)


func test_wrong_types_in_file_keep_defaults() -> void:
	var config := ConfigFile.new()
	config.set_value(Settings.SECTION, "volume", "loud")
	config.set_value(Settings.SECTION, "fullscreen", 1)
	config.save(PATH)
	var loaded := Settings.load_from(PATH)
	assert_eq(loaded.volume, 1.0)
	assert_false(loaded.fullscreen)


func test_out_of_range_values_are_clamped() -> void:
	var config := ConfigFile.new()
	config.set_value(Settings.SECTION, "volume", 3.0)
	config.set_value(Settings.SECTION, "orbit_speed", -1.0)
	config.save(PATH)
	var loaded := Settings.load_from(PATH)
	assert_eq(loaded.volume, 1.0)
	assert_eq(loaded.orbit_speed, 0.0)


func test_whole_numbers_in_file_are_read_as_floats() -> void:
	var config := ConfigFile.new()
	config.set_value(Settings.SECTION, "volume", 0)
	config.set_value(Settings.SECTION, "orbit_speed", 2)
	config.save(PATH)
	var loaded := Settings.load_from(PATH)
	assert_eq(loaded.volume, 0.0)
	assert_eq(loaded.orbit_speed, 2.0)
