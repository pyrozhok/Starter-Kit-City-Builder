extends GutTest

const SAVE_PATH := "user://test_builder_map.res"

var builder: Builder
var viewport: SubViewport  # own viewport: GUT's panel can't be the hovered Control

func before_each() -> void:
	builder = Builder.new()
	builder.structures.assign([load("res://structures/road-straight.tres"), load("res://structures/grass.tres")])
	builder.gridmap = GridMap.new()
	builder.selector = Node3D.new()
	builder.selector_container = Node3D.new()
	builder.cash_display = Label.new()
	builder.add_child(builder.gridmap)
	builder.add_child(builder.selector)
	builder.selector.add_child(builder.selector_container)
	builder.add_child(builder.cash_display)
	viewport = SubViewport.new()
	add_child_autofree(viewport)
	viewport.add_child(builder)
	builder.set_process(false)  # after entering the tree (READY turns _process on); _process needs a camera, drive actions directly

func after_each() -> void:
	for action: String in ["build", "demolish", "structure_next", "structure_previous"]:
		Input.action_release(action)
	if FileAccess.file_exists(SAVE_PATH):
		DirAccess.remove_absolute(SAVE_PATH)

func test_build_charges_price_and_places_tile() -> void:
	var cash_before: int = builder.map.cash
	Input.action_press("build")
	builder.action_build(Vector3(2, 0, 3))
	assert_eq(builder.gridmap.get_cell_item(Vector3i(2, 0, 3)), 0)
	assert_eq(builder.map.cash, cash_before - builder.structures[0].price)
	assert_eq(builder.cash_display.text, "$" + str(builder.map.cash))

func test_demolish_empties_tile() -> void:
	builder.gridmap.set_cell_item(Vector3i(2, 0, 3), 1)
	Input.action_press("demolish")
	builder.action_demolish(Vector3(2, 0, 3))
	assert_eq(builder.gridmap.get_cell_item(Vector3i(2, 0, 3)), -1)

func test_preview_is_not_rebuilt_without_toggle() -> void:
	var preview: Node = builder.selector_container.get_child(0)
	builder.action_structure_toggle()  # nothing pressed, like an idle _process frame
	assert_eq(builder.selector_container.get_child_count(), 1)
	assert_same(builder.selector_container.get_child(0), preview)

func test_structure_next_switches_preview() -> void:
	var preview: Node = builder.selector_container.get_child(0)
	Input.action_press("structure_next")
	builder.action_structure_toggle()
	assert_eq(builder.index, 1)
	assert_eq(builder.selector_container.get_child_count(), 1)
	assert_ne(builder.selector_container.get_child(0), preview)
	await get_tree().process_frame  # let the replaced preview's queue_free() run before GUT counts orphans

func test_structure_previous_from_first_wraps_to_last_and_switches_preview() -> void:
	# A third structure: with two, previous and next both take 0 to 1 and can't be told apart.
	builder.structures.append(load("res://structures/pavement.tres"))
	var preview: Node = builder.selector_container.get_child(0)
	Input.action_press("structure_previous")
	builder.action_structure_toggle()
	assert_eq(builder.index, 2)  # 0 - 1 wraps to the last one (next would give 1)
	assert_eq(builder.selector_container.get_child_count(), 1)
	assert_ne(builder.selector_container.get_child(0), preview)
	assert_eq(builder.selector_container.get_child(0).scene_file_path, "res://models/pavement.glb")
	await get_tree().process_frame  # let the replaced preview's queue_free() run before GUT counts orphans

func test_save_map_writes_tiles_and_emits_map_saved() -> void:
	watch_signals(builder)
	builder.gridmap.set_cell_item(Vector3i(1, 0, 2), 1)
	assert_true(builder.save_map(SAVE_PATH))
	assert_signal_emitted(builder, "map_saved")
	var saved: DataMap = ResourceLoader.load(SAVE_PATH, "", ResourceLoader.CACHE_MODE_IGNORE)
	assert_eq(saved.structures.size(), 1)
	assert_eq(saved.structures[0].position, Vector2i(1, 2))
	assert_eq(saved.structures[0].structure, 1)


func test_load_map_restores_tiles_cash_and_emits_map_loaded() -> void:
	var map := DataMap.new()
	map.cash = 1234
	var cell := DataStructure.new()
	cell.position = Vector2i(4, -1)
	cell.structure = 1
	map.structures.append(cell)
	ResourceSaver.save(map, SAVE_PATH)
	watch_signals(builder)
	assert_true(builder.load_map(SAVE_PATH))
	assert_eq(builder.gridmap.get_cell_item(Vector3i(4, 0, -1)), 1)
	assert_eq(builder.cash_display.text, "$1234")
	assert_signal_emitted(builder, "map_loaded")


func test_load_map_quietly_does_not_emit_map_loaded() -> void:
	ResourceSaver.save(DataMap.new(), SAVE_PATH)
	watch_signals(builder)
	assert_true(builder.load_map(SAVE_PATH, false))
	assert_signal_not_emitted(builder, "map_loaded")


func test_load_map_without_file_clears_map_and_returns_false() -> void:
	builder.gridmap.set_cell_item(Vector3i(0, 0, 0), 1)
	watch_signals(builder)
	assert_false(builder.load_map("user://no_such_map.res"))
	assert_eq(builder.gridmap.get_used_cells().size(), 0)
	assert_eq(builder.map.cash, DataMap.new().cash)
	assert_signal_not_emitted(builder, "map_loaded")


func test_new_map_clears_tiles_and_resets_cash() -> void:
	builder.gridmap.set_cell_item(Vector3i(0, 0, 0), 1)
	builder.map.cash = 5
	builder.new_map()
	assert_eq(builder.gridmap.get_used_cells().size(), 0)
	assert_eq(builder.cash_display.text, "$" + str(DataMap.new().cash))


func test_set_active_false_stops_processing_and_hides_selector() -> void:
	builder.set_active(false)
	assert_false(builder.is_processing())
	assert_false(builder.selector.visible)
	builder.set_active(true)
	assert_true(builder.is_processing())
	assert_true(builder.selector.visible)


func _hover_new_button() -> Button:
	var button := Button.new()
	button.size = Vector2(200, 200)
	viewport.add_child(button)
	var motion := InputEventMouseMotion.new()
	motion.position = Vector2(50, 50)
	motion.global_position = motion.position
	viewport.push_input(motion)
	return button


func test_build_is_ignored_while_pointer_is_over_ui() -> void:
	var button := _hover_new_button()
	assert_eq(viewport.gui_get_hovered_control(), button, "precondition: button hovered")
	var cash_before: int = builder.map.cash
	Input.action_press("build")
	builder.action_build(Vector3(2, 0, 3))
	assert_eq(builder.gridmap.get_cell_item(Vector3i(2, 0, 3)), GridMap.INVALID_CELL_ITEM)
	assert_eq(builder.map.cash, cash_before)


func test_demolish_is_ignored_while_pointer_is_over_ui() -> void:
	builder.gridmap.set_cell_item(Vector3i(2, 0, 3), 0)
	_hover_new_button()
	Input.action_press("demolish")
	builder.action_demolish(Vector3(2, 0, 3))
	assert_eq(builder.gridmap.get_cell_item(Vector3i(2, 0, 3)), 0)


func test_reload_without_saving_restores_saved_cash() -> void:
	var saved := DataMap.new()
	saved.cash = 500
	ResourceSaver.save(saved, SAVE_PATH)
	builder.load_map(SAVE_PATH)
	Input.action_press("build")
	builder.action_build(Vector3(0, 0, 0))  # spends cash on the loaded map object
	builder.load_map(SAVE_PATH)
	assert_eq(builder.map.cash, 500)
	assert_eq(builder.gridmap.get_used_cells().size(), 0)


func test_rebuilding_same_structure_on_its_tile_does_not_charge() -> void:
	Input.action_press("build")
	builder.action_build(Vector3(2, 0, 3))  # first build: pays for structure 0
	var cash_after_first: int = builder.map.cash
	builder.action_build(Vector3(2, 0, 3))  # same structure, same tile
	assert_eq(builder.gridmap.get_cell_item(Vector3i(2, 0, 3)), 0)
	assert_eq(builder.map.cash, cash_after_first)
	assert_eq(builder.cash_display.text, "$" + str(cash_after_first))
