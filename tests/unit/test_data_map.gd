extends GutTest

const SAVE_PATH := "user://test_map.res"


func after_each() -> void:
	if FileAccess.file_exists(SAVE_PATH):
		DirAccess.remove_absolute(SAVE_PATH)


func test_new_map_starts_with_default_cash() -> void:
	var map := DataMap.new()
	assert_eq(map.cash, 10000)
	assert_eq(map.structures.size(), 0)


func test_map_round_trips_through_resource_saver() -> void:
	var map := DataMap.new()
	map.cash = 4321
	var cell := DataStructure.new()
	cell.position = Vector2i(3, -2)
	cell.orientation = 10
	cell.structure = 5
	map.structures.append(cell)

	assert_eq(ResourceSaver.save(map, SAVE_PATH), OK)
	var loaded: DataMap = ResourceLoader.load(SAVE_PATH, "", ResourceLoader.CACHE_MODE_IGNORE)

	assert_not_null(loaded)
	assert_eq(loaded.cash, 4321)
	assert_eq(loaded.structures.size(), 1)
	assert_eq(loaded.structures[0].position, Vector2i(3, -2))
	assert_eq(loaded.structures[0].orientation, 10)
	assert_eq(loaded.structures[0].structure, 5)
