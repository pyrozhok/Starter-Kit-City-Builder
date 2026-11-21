class_name Notifications
extends MenuPanel
## Mockup "Notifications": newest on top, at most MAX_ITEMS, a dot on items not yet seen.
## Hidden while empty. Hovering the panel marks everything read.
## With auto_hide on (while playing) the panel hides hide_delay seconds after the last push,
## so it doesn't keep blocking building under it; it waits while the pointer is over it.

const MAX_ITEMS := 3
const ITEM_SCENE := preload("res://scenes/ui/notification_item.tscn")

@export var hide_delay := 5.0 ## Seconds after the last push before an auto-hiding panel hides

## Off (in the menu): visible whenever there are items. On (playing): hides after hide_delay.
var auto_hide := false:
	set(value):
		auto_hide = value
		if not is_node_ready():
			return
		if value:
			if visible:
				_restart_hide_timer()
		else:
			_hide_timer.stop()
			visible = _list.get_child_count() > 0

var _hovered := false
var _hide_timer := Timer.new()

@onready var _list: VBoxContainer = $List


func _ready() -> void:
	super()  # moves scene children into the content slot, so the timer is added after it
	_hide_timer.one_shot = true
	add_child(_hide_timer)
	visible = _list.get_child_count() > 0
	_hide_timer.timeout.connect(_on_hide_timeout)
	mouse_entered.connect(_on_mouse_entered)
	mouse_exited.connect(_on_mouse_exited)


func push(text: String) -> void:
	var item: NotificationItem = ITEM_SCENE.instantiate()
	item.text = text
	item.time = "just now"
	item.unread = true
	_list.add_child(item)
	_list.move_child(item, 0)
	while _list.get_child_count() > MAX_ITEMS:
		var oldest := _list.get_child(-1)
		_list.remove_child(oldest)
		oldest.queue_free()
	_name_items()
	show()
	if auto_hide:
		_restart_hide_timer()


# Item1 is the newest, as in the mockup; stable names for screenshot layout checks.
func _name_items() -> void:
	for item in items():
		item.name = "_" + item.name  # clear the target names first: siblings can't share one
	for i in _list.get_child_count():
		_list.get_child(i).name = "Item%d" % (i + 1)


func items() -> Array[NotificationItem]:
	var out: Array[NotificationItem] = []
	out.assign(_list.get_children())
	return out


func mark_all_read() -> void:
	for item in items():
		item.unread = false


func _restart_hide_timer() -> void:
	_hide_timer.start(hide_delay)


func _on_hide_timeout() -> void:
	if not _hovered:
		hide()  # mouse_exited restarts the timer otherwise


func _on_mouse_entered() -> void:
	_hovered = true
	mark_all_read()


func _on_mouse_exited() -> void:
	_hovered = false
	if auto_hide and visible:
		_restart_hide_timer()
