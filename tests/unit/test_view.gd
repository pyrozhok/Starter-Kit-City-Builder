extends GutTest

var view: View


func before_each() -> void:
	view = View.new()
	var camera := Camera3D.new()
	camera.name = "Camera"
	view.add_child(camera)
	view.set_process(false)  # drive _process by hand with a fixed delta
	add_child_autofree(view)


func after_each() -> void:
	Input.action_release("camera_right")


func test_camera_moves_on_input_by_default() -> void:
	Input.action_press("camera_right")
	view._process(0.1)
	assert_ne(view.camera_position, Vector3.ZERO)


func test_input_disabled_ignores_camera_input() -> void:
	view.input_enabled = false
	Input.action_press("camera_right")
	view._process(0.1)
	assert_eq(view.camera_position, Vector3.ZERO)


func test_auto_orbit_turns_camera_around_center() -> void:
	var yaw_before: float = view.camera_rotation.y
	view.auto_orbit = true
	view._process(0.5)
	assert_almost_eq(view.camera_rotation.y, yaw_before + view.ORBIT_SPEED * 0.5, 0.001)
