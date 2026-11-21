// Backdrop blur for translucent panels (mockup effect "backgroundBlur").
// Put it on a Panel drawn behind the real panel (show_behind_parent): the Panel's StyleBox gives the
// shape (alpha, rounded corners), this shader fills it with the blurred screen; the parent's
// translucent StyleBox then tints it.
shader_type canvas_item;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
// Mip level: 3 ≈ a 16px blur radius at 1080p.
uniform float lod : hint_range(0.0, 6.0) = 3.0;

void fragment() {
	COLOR = vec4(textureLod(screen_texture, SCREEN_UV, lod).rgb, COLOR.a);
}
