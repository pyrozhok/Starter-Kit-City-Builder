# GUT fixtures

Real output of Godot 4.7.2 and GUT 9.7.1, run headless with the same arguments as `run_tests`, in a
`git archive HEAD` copy of the project with throwaway test scripts. Home paths are replaced by `~/`;
ANSI colour codes are kept.

- `gut-9.7.1-orphans.*`: `test_leak_a.gd` leaks 1 `Node`, `test_leak_b.gd` leaks 2 (and has one clean test). Exit 0.
- `gut-9.7.1-parse-error.*` and `gut-9.7.1-mixed.junit.xml`: `test_mixed.gd` with a passing, a
  failing (`assert_eq(2, 3, "two is not three")`) and a pending test, plus `test_broken.gd` that
  doesn't parse (`var x: int = "not an int"`). Exit 1.
