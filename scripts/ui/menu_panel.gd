class_name MenuPanel
extends PanelContainer
## Mockup component "Panel": header, divider, content slot.
## Nodes added as children of a MenuPanel instance in a scene move into the content slot on ready.

@export var title := "PANEL":
	set(value):
		title = value
		if is_node_ready():
			_header.text = value
## Smaller padding, gap and left-aligned header (the notifications variant in the mockup).
@export var compact := false
## Theme variation of the content slot, for an instance that overrides its gap (Options: 8).
@export var content_variation := &""

@onready var content: VBoxContainer = $Box/Content
@onready var _box: VBoxContainer = $Box
@onready var _blur: Panel = $Blur
@onready var _header: Label = $Box/Header


func _ready() -> void:
	_header.text = title
	content.theme_type_variation = content_variation
	if compact:
		theme_type_variation = &"MenuPanelSmall"
		_box.theme_type_variation = &"MenuPanelBoxSmall"
		_header.theme_type_variation = &"PanelHeaderSmall"
		_header.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	for child: Node in get_children():
		if child != _box and child != _blur:
			child.reparent(content, false)
