class_name Notifications
extends MenuPanel
## Mockup "Notifications": newest on top, at most MAX_ITEMS, a dot on items not yet seen.
## Hidden while empty. Hovering the panel marks everything read.

const MAX_ITEMS := 3
const ITEM_SCENE := preload("res://scenes/ui/notification_item.tscn")

@onready var _list: VBoxContainer = $List


func _ready() -> void:
	super()
	visible = _list.get_child_count() > 0
	mouse_entered.connect(mark_all_read)


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
	show()


func items() -> Array[NotificationItem]:
	var out: Array[NotificationItem] = []
	out.assign(_list.get_children())
	return out


func mark_all_read() -> void:
	for item in items():
		item.unread = false
