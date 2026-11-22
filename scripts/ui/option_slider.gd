class_name OptionSlider
extends HSlider
## Mockup component "Slider". The theme shows Normal and Hover; Pressed (being dragged) is its own
## variation because HSlider has one highlight for both.

## On: the Pressed look. Follows the drag; set it directly only for previews.
var dragging := false:
	set(value):
		dragging = value
		theme_type_variation = &"OptionSliderPressed" if value else &"OptionSlider"


func _ready() -> void:
	drag_started.connect(func() -> void: dragging = true)
	drag_ended.connect(func(_changed: bool) -> void: dragging = false)
