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
	assert_almost_eq(view.camera_rotation.y, yaw_before + 3.0 * 0.5, 0.001, "default orbit is 3 deg/s")


func test_orbit_speed_is_tunable() -> void:
	var yaw_before: float = view.camera_rotation.y
	view.auto_orbit = true
	view.orbit_speed = 10.0
	view._process(0.5)
	assert_almost_eq(view.camera_rotation.y, yaw_before + 5.0, 0.001)


func test_reset_returns_to_start_angle_the_short_way() -> void:
	var home: Vector3 = view.camera_rotation
	view.camera_position = Vector3(5, 0, 5)
	view.camera_rotation.y += 725.0  # two laps of orbit and 5 degrees
	view.rotation_degrees = view.camera_rotation
	view.reset()
	assert_eq(view.camera_position, Vector3.ZERO)
	assert_almost_eq(fposmod(view.camera_rotation.y - home.y, 360.0), 0.0, 0.001, "start angle")
	assert_almost_eq(view.rotation_degrees.y - view.camera_rotation.y, 5.0, 0.001, "turns back 5 degrees, not 725")

# A tap: hold for a frame, release, poll in the release frame, let the frame end.
func _tap(action: String) -> void:
	Input.action_press(action)
	await wait_process_frames(1)
	Input.action_release(action)
	view.handle_input(0.1)
	await wait_process_frames(1)

func test_zoom_in_stops_at_15_meters() -> void:
	view.zoom = 20.0
	for i in 3:
		await _tap("zoom_in")
	assert_eq(view.zoom, 15.0)

func test_zoom_out_stops_at_80_meters() -> void:
	view.zoom = 75.0
	for i in 3:
		await _tap("zoom_out")
	assert_eq(view.zoom, 80.0)
