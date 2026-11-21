class_name View
extends Node3D

@export var orbit_speed := 3.0 # Degrees per second while auto_orbit is on

var input_enabled := true # Off: camera ignores the player (e.g. under a menu)
var auto_orbit := false # On: camera slowly turns around its target

var camera_position:Vector3
var camera_rotation:Vector3

var zoom:float = 30.0 # 30 = Standard zoom level, in meters

@onready var camera = $Camera

func _ready():
	
	camera_rotation = rotation_degrees # Initial rotation
	
	pass

func _process(delta):
	
	# Set position and rotation to targets
	
	position = position.lerp(camera_position, delta * 8)
	rotation_degrees = rotation_degrees.lerp(camera_rotation, delta * 6)
	
	# Smoothly update zoom
	
	camera.position = camera.position.lerp(Vector3(0, 0, zoom), delta * 8)
	
	if auto_orbit:
		camera_rotation.y += orbit_speed * delta
	
	if input_enabled:
		handle_input(delta)

# Handle input

func handle_input(_delta):
	
	# Rotation
	
	var input := Vector3.ZERO
	
	input.x = Input.get_axis("camera_left", "camera_right")
	input.z = Input.get_axis("camera_forward", "camera_back")
	
	input = input.rotated(Vector3.UP, rotation.y).normalized()
	
	camera_position += input / 4
	
	# Zoom in/out
	
	if Input.is_action_just_released("zoom_in"):
		zoom = max(15, zoom - 5) # 15 = Minimum zoom level, in meters
		
	if Input.is_action_just_released("zoom_out"):
		zoom = min(80, zoom + 5) # 80 = Maximum zoom level, in meters
	
	# Back to center
	
	if Input.is_action_pressed("camera_center"):
		camera_position = Vector3()

func _input(event):
	
	if not input_enabled:
		return
	
	# Rotate camera using mouse (hold 'middle' mouse button)
	
	if event is InputEventMouseMotion:
		if Input.is_action_pressed("camera_rotate"):
			camera_rotation += Vector3(0, -event.relative.x / 10, 0)
