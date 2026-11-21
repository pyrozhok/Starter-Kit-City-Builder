# GUT fixtures

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
