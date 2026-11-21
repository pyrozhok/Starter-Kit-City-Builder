extends GutTest

var panel: Notifications


func before_each() -> void:
	panel = (load("res://scenes/ui/notifications.tscn") as PackedScene).instantiate()
	add_child_autofree(panel)


func test_starts_hidden_and_empty() -> void:
	assert_false(panel.visible)
	assert_eq(panel.items().size(), 0)


func test_push_shows_unread_item_on_top() -> void:
	panel.push("Map loaded")
	panel.push("Map saved")
	assert_true(panel.visible)
	var items := panel.items()
	assert_eq(items[0].text, "Map saved")
	assert_eq(items[0].time, "just now")
	assert_true(items[0].unread)
	assert_eq(items[1].text, "Map loaded")
	assert_eq([items[0].name, items[1].name], [&"Item1", &"Item2"], "named top-down like the mockup")


func test_keeps_only_three_newest() -> void:
	for text: String in ["one", "two", "three", "four"]:
		panel.push(text)
	var texts: Array = panel.items().map(func(item: NotificationItem) -> String: return item.text)
	assert_eq(texts, ["four", "three", "two"])
	await get_tree().process_frame  # let the dropped item's queue_free() run before GUT counts orphans


func test_mark_all_read_clears_dots() -> void:
	panel.push("Map saved")
	panel.mark_all_read()
	assert_false(panel.items()[0].unread)


func test_hover_marks_all_read() -> void:
	panel.push("Map saved")
	panel.mouse_entered.emit()
	assert_false(panel.items()[0].unread)


func test_without_auto_hide_stays_visible() -> void:
	panel.hide_delay = 0.05
	panel.push("Map saved")
	await wait_seconds(0.1)
	assert_true(panel.visible)


func test_auto_hide_hides_after_last_push() -> void:
	panel.hide_delay = 0.05
	panel.auto_hide = true
	panel.push("Map saved")
	assert_true(panel.visible)
	await wait_seconds(0.1)
	assert_false(panel.visible)


func test_auto_hide_waits_while_hovered() -> void:
	panel.hide_delay = 0.05
	panel.auto_hide = true
	panel.push("Map saved")
	panel.mouse_entered.emit()
	await wait_seconds(0.1)
	assert_true(panel.visible, "pointer is over it")
	panel.mouse_exited.emit()
	await wait_seconds(0.1)
	assert_false(panel.visible)


func test_turning_auto_hide_off_shows_items_again() -> void:
	panel.hide_delay = 0.05
	panel.auto_hide = true
	panel.push("Map saved")
	await wait_seconds(0.1)
	panel.auto_hide = false
	assert_true(panel.visible, "in the menu the panel shows whenever it has items")
