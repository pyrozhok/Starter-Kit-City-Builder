class_name NotificationItem
extends MarginContainer
## Mockup component "NotificationItem": unread dot, text, time.

@export var text := "Notification text":
	set(value):
		text = value
		if is_node_ready():
			_text.text = value
@export var time := "now":
	set(value):
		time = value
		if is_node_ready():
			_time.text = value
@export var unread := true:
	set(value):
		unread = value
		if is_node_ready():
			_dot.modulate.a = 1.0 if value else 0.0  # the slot keeps its width either way

@onready var _dot: Panel = $Row/DotSlot/Dot
@onready var _text: Label = $Row/Text
@onready var _time: Label = $Row/Time


func _ready() -> void:
	text = text
	time = time
	unread = unread
