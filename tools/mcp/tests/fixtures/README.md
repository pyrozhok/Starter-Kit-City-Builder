# Godot fixtures

## GUT runs

Each capture `gut-9.7.1-<name>` is one real run of Godot 4.7.2 and GUT 9.7.1, headless, with the
arguments `run_tests` passes (`-gdir=res://tests/<dir>`), in a `git archive HEAD` copy of the project
with throwaway test scripts: `.stdout.txt`, `.stderr.txt` and the `.junit.xml` it wrote. Home paths
are replaced by `~/`; ANSI colour codes are kept. `FakeGodot.on(capture=...)` replays one.

| Capture | Test scripts | Exit |
|---|---|---|
| `orphans` | `test_leak_a.gd` leaks 1 `Node`; `test_leak_b.gd` leaks 2 and has one clean test | 0 |
| `mixed` | `test_mixed.gd`: one passing, one failing (`assert_eq(2, 3, "two is not three")`), one pending; `test_broken.gd` doesn't parse (`var x: int = "not an int"`) | 1 |
| `skipped-script` | `test_ok.gd` passes; `test_broken.gd` as above | 0 |
| `nothing-ran` | an empty directory | 0 |
| `push-error` | `push_error("boom from the test")`, then `assert_true(true)` | 1 |

## Screenshot runs

Each capture `screenshot-4.7.2-<name>` is one real windowed run of `tools/mcp/screenshot.gd` (Godot
4.7.2, Vulkan, Wayland) with the arguments `screenshot` passes, in a `git archive HEAD` copy:
`.stdout.txt`, `.stderr.txt` and the `.layout.json` it wrote (the PNG isn't kept; `screenshot` only
checks that it exists). The output directory is replaced by `<out>/`, the GPU name by `<GPU>`.

| Capture | Scene and arguments | Exit |
|---|---|---|
| `ok` | `scenes/main.tscn`, `--state=save`, 1920×1080, 30 frames | 0 |
| `blank` | a `Control` with nothing in it | 0 |
| `script-error` | a red `ColorRect` under a root whose `_ready()` calls `queue_free()` on null | 0 |
| `shader-error` | `scenes/ui/main_menu.tscn` with `COLOR = undefined_thing;` added to `backdrop_blur.gdshader` | 0 |
| `hover-missing` | `scenes/main.tscn`, `--hover=Nope` (no layout: nothing was written) | 1 |
