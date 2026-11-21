extends GutTest

var builder

func before_each() -> void:
	builder = load("res://scripts/builder.gd").new()
	builder.structures.assign([load("res://structures/road-straight.tres"), load("res://structures/grass.tres")])
	builder.gridmap = GridMap.new()
	builder.selector = Node3D.new()
	builder.selector_container = Node3D.new()
	builder.cash_display = Label.new()
	builder.add_child(builder.gridmap)
	builder.add_child(builder.selector)
	builder.selector.add_child(builder.selector_container)
	builder.add_child(builder.cash_display)
	builder.set_process(false)  # _process needs a camera; drive actions directly
	add_child_autofree(builder)

func after_each() -> void:
	for action in ["build", "structure_next", "structure_previous"]:
		Input.action_release(action)

func test_build_charges_price_and_places_tile() -> void:
	var cash_before: int = builder.map.cash
	Input.action_press("build")
	builder.action_build(Vector3(2, 0, 3))
	assert_eq(builder.gridmap.get_cell_item(Vector3i(2, 0, 3)), 0)
	assert_eq(builder.map.cash, cash_before - builder.structures[0].price)
	assert_eq(builder.cash_display.text, "$" + str(builder.map.cash))
