class_name Settings
extends RefCounted
## Player settings, kept in a ConfigFile apart from the map save. Values read from the file are
## type-checked and clamped: it is the player's to edit.

const PATH := "user://settings.cfg"
const SECTION := "settings"
const ORBIT_SPEED_MAX := 2.0

## Master bus volume, linear 0–1.
var volume := 1.0
var fullscreen := false
## Menu backdrop orbit as a multiplier on View.orbit_speed, 0–ORBIT_SPEED_MAX.
var orbit_speed := 1.0


func save(path: String) -> Error:
	var config := ConfigFile.new()
	config.set_value(SECTION, "volume", volume)
	config.set_value(SECTION, "fullscreen", fullscreen)
	config.set_value(SECTION, "orbit_speed", orbit_speed)
	return config.save(path)


## Defaults for a missing file and for each missing or mistyped value.
static func load_from(path: String) -> Settings:
	var settings := Settings.new()
	var config := ConfigFile.new()
	if config.load(path) != OK:
		return settings
	var value: Variant = config.get_value(SECTION, "volume", settings.volume)
	if value is float:
		settings.volume = clampf(value, 0.0, 1.0)
	value = config.get_value(SECTION, "fullscreen", settings.fullscreen)
	if value is bool:
		settings.fullscreen = value
	value = config.get_value(SECTION, "orbit_speed", settings.orbit_speed)
	if value is float:
		settings.orbit_speed = clampf(value, 0.0, ORBIT_SPEED_MAX)
	return settings
