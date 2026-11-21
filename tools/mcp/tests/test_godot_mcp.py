"""Tests for tools/mcp/godot_mcp.py, the `godot` MCP server. Plan: issue #2. No Godot needed."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import ModuleType

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Keys of a finished Godot run (`_godot`); a run that never finished returns the same ones.
RUN_KEYS = {"ok", "exit_code", "errors", "output_tail", "orphans"}


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text()


def run_result(ok: bool = True, exit_code: int = 0, errors: list[str] | None = None,
               output_tail: str = "", orphans: int = 0) -> dict:
    """What `_godot` returns for a finished run; stubs of `_godot` return this."""
    return {"ok": ok, "exit_code": exit_code, "errors": errors or [], "output_tail": output_tail,
            "orphans": orphans}


# --- 1. _godot and _failure ----------------------------------------------------------------


def test_missing_binary_is_a_failure_without_exit_code(mod: ModuleType) -> None:
    result = mod._godot(["--version"], timeout=5)

    assert result["ok"] is False
    assert result["exit_code"] is None
    assert result["errors"][0].startswith("Godot binary not found")


def test_timeout_keeps_what_godot_printed(mod: ModuleType, fake_godot) -> None:
    fake_godot(stderr="ERROR: still importing\n", sleep=30)

    result = mod._godot(["--import"], timeout=1)

    assert result["ok"] is False
    assert result["exit_code"] is None
    assert result["errors"][0].startswith("Timed out after 1s")
    assert "still importing" in result["output_tail"]


def test_run_that_never_finished_has_the_keys_of_a_finished_run(mod: ModuleType, fake_godot) -> None:
    missing = mod._godot(["--import"], timeout=5)
    fake_godot(stdout="done\n")
    finished = mod._godot(["--import"], timeout=5)

    assert set(finished) == RUN_KEYS
    assert set(missing) == RUN_KEYS


def test_ansi_codes_are_stripped(mod: ModuleType, fake_godot) -> None:
    fake_godot(stderr="\x1b[1;31mERROR: red text\x1b[0m\n")

    result = mod._godot([], timeout=5)

    assert result["errors"] == ["ERROR: red text"]
    assert "\x1b" not in result["output_tail"]


def test_at_line_is_appended_to_its_error(mod: ModuleType, fake_godot) -> None:
    fake_godot(stdout=fixture_text("gut-9.7.1-parse-error.stdout.txt"),
               stderr=fixture_text("gut-9.7.1-parse-error.stderr.txt"), code=1)

    result = mod._godot([], timeout=5)

    # The engine's own `at:` line names a C++ file, not res://, so it adds nothing; the GDScript
    # backtrace lines that follow aren't `at:` lines.
    assert result["errors"] == [
        'SCRIPT ERROR: Parse Error: Cannot assign a value of type "String" as "int". '
        "[res://tests/mixed/test_broken.gd:5]",
        'SCRIPT ERROR: Parse Error: Cannot assign a value of type String to variable "x" with '
        "specified type int. [res://tests/mixed/test_broken.gd:5]",
        'ERROR: Failed to load script "res://tests/mixed/test_broken.gd" with error "Parse error".',
    ]


def test_duplicate_errors_are_collapsed(mod: ModuleType, fake_godot) -> None:
    fake_godot(stderr="ERROR: same\nERROR: same\nWARNING: other\nERROR: same\n")

    assert mod._godot([], timeout=5)["errors"] == ["ERROR: same", "WARNING: other"]


@pytest.mark.parametrize(("stderr", "ok"), [
    ("ERROR: Failed to load resource\n", False),
    ("SCRIPT ERROR: Parse Error: x\n", False),
    ("USER ERROR: boom\n", False),
    (fixture_text("gut-9.7.1-orphans.stderr.txt"), True),  # WARNING only
])
def test_ok_on_exit_0_depends_on_error_lines(mod: ModuleType, fake_godot, stderr: str, ok: bool) -> None:
    fake_godot(stderr=stderr, code=0)

    assert mod._godot([], timeout=5)["ok"] is ok


def test_nonzero_exit_is_not_ok(mod: ModuleType, fake_godot) -> None:
    fake_godot(code=1)

    result = mod._godot([], timeout=5)

    assert result["ok"] is False
    assert result["exit_code"] == 1


# --- 2. Orphan parsing ---------------------------------------------------------------------


def test_orphans_are_summed_over_test_scripts(mod: ModuleType, fake_godot) -> None:
    # Real output: test_leak_a.gd leaked 1 node, test_leak_b.gd leaked 2.
    fake_godot(stdout=fixture_text("gut-9.7.1-orphans.stdout.txt"),
               stderr=fixture_text("gut-9.7.1-orphans.stderr.txt"))

    assert mod._godot([], timeout=5)["orphans"] == 3


def test_per_test_and_summary_orphan_lines_are_not_counted(mod: ModuleType, fake_godot) -> None:
    lines = fixture_text("gut-9.7.1-orphans.stdout.txt").splitlines(keepends=True)
    # GUT writes the script-level line as "<n> orphans"; per-test and summary lines say "Orphans".
    script_lines = [line for line in lines if "orphans" in line]
    assert len(script_lines) == 2
    fake_godot(stdout="".join(line for line in lines if line not in script_lines))

    assert mod._godot([], timeout=5)["orphans"] == 0


# --- 3. _git_snapshot and files_changed_by_build -------------------------------------------


def _build_doing(mod: ModuleType, monkeypatch: pytest.MonkeyPatch, change) -> dict:
    """Run `build` with a stubbed Godot whose import step does `change(ROOT)`."""

    def fake(args: list[str], timeout: int, headless: bool = True) -> dict:
        if args == ["--import"]:
            change(mod.ROOT)
        return run_result()

    monkeypatch.setattr(mod, "_godot", fake)
    return mod.build()


def _write(name: str, text: str):
    return lambda root: (root / name).write_text(text)


def _nothing(root: Path) -> None:
    pass


@pytest.mark.parametrize(("setup", "change", "expected"), [
    pytest.param(_nothing, _nothing, [], id="nothing-on-clean-tree"),
    pytest.param(_nothing, _write("new.gd.uid", "uid://x\n"), ["new.gd.uid"], id="creates-untracked"),
    pytest.param(_nothing, _write("tracked.txt", "b\n"), ["tracked.txt"], id="rewrites-clean-tracked"),
    pytest.param(_write("dirty.txt", "b\n"), _write("dirty.txt", "c\n"), ["dirty.txt"],
                 id="changes-dirty-again"),
    pytest.param(_write("dirty.txt", "b\n"), _write("dirty.txt", "a\n"), ["dirty.txt"],
                 id="restores-dirty-to-head"),
    pytest.param(_write("untracked.txt", "x\n"), lambda root: (root / "untracked.txt").unlink(),
                 ["untracked.txt"], id="deletes-untracked"),
    pytest.param(_write("dirty.txt", "b\n"), _nothing, [], id="leaves-dirty-alone"),
    pytest.param(_write("ignored.txt", "x\n"), _write("ignored.txt", "y\n"), [], id="changes-ignored"),
])
def test_files_changed_by_build(mod: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch,
                                setup, change, expected: list[str]) -> None:
    setup(repo)

    assert _build_doing(mod, monkeypatch, change)["files_changed_by_build"] == expected


def test_files_changed_by_build_is_empty_outside_a_git_repo(mod: ModuleType,
                                                           monkeypatch: pytest.MonkeyPatch) -> None:
    result = _build_doing(mod, monkeypatch, _write("new.gd.uid", "uid://x\n"))

    assert result["files_changed_by_build"] == []


# --- 4. run_tests and JUnit parsing --------------------------------------------------------


@pytest.fixture
def gut(mod: ModuleType) -> ModuleType:
    """ROOT with GUT installed (only the file run_tests checks for)."""
    cmdln = mod.ROOT / "addons/gut/gut_cmdln.gd"
    cmdln.parent.mkdir(parents=True)
    cmdln.write_text("extends SceneTree\n")
    return mod


def _stub_run(mod: ModuleType, monkeypatch: pytest.MonkeyPatch, junit: str | None = None,
              **run) -> list[list[str]]:
    """Stub `_godot`: writes `junit` (text) to RESULTS_XML and returns run_result(**run).
    Returns the list the stub appends each call's args to."""
    calls: list[list[str]] = []

    def fake(args: list[str], timeout: int, headless: bool = True) -> dict:
        calls.append(args)
        if junit is not None:
            mod.RESULTS_XML.parent.mkdir(parents=True, exist_ok=True)
            mod.RESULTS_XML.write_text(junit)
        return run_result(**run)

    monkeypatch.setattr(mod, "_godot", fake)
    return calls


def test_passed_failed_and_pending_are_counted(gut: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_run(gut, monkeypatch, fixture_text("gut-9.7.1-mixed.junit.xml"), ok=False, exit_code=1)

    result = gut.run_tests()

    assert (result["passed"], result["failed"], result["pending"]) == (1, 1, 1)
    assert result["failures"] == [{
        "test": "tests/mixed/test_mixed.gd::test_fails",
        "message": "[2] expected to equal [3]: two is not three at line 9",
    }]
    assert result["ok"] is False


def test_failure_without_body_falls_back_to_message(gut: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    junit = ('<testsuites><testsuite name="t"><testcase name="test_x" classname="tests/t.gd">'
             '<failure message="boom"/></testcase></testsuite></testsuites>')
    _stub_run(gut, monkeypatch, junit, ok=False, exit_code=1)

    assert gut.run_tests()["failures"] == [{"test": "tests/t.gd::test_x", "message": "boom"}]


def test_truncated_junit_is_reported_as_missing(gut: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    junit = fixture_text("gut-9.7.1-mixed.junit.xml")
    _stub_run(gut, monkeypatch, junit[: len(junit) // 2], ok=False, exit_code=None)

    result = gut.run_tests()

    assert result["ok"] is False
    assert "No JUnit results produced; see output_tail" in result["errors"]


def test_no_junit_reports_godot_errors_and_the_missing_file(gut: ModuleType,
                                                            monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_run(gut, monkeypatch, None, ok=False, exit_code=1, errors=["ERROR: boom"])

    errors = gut.run_tests()["errors"]

    assert "ERROR: boom" in errors
    assert "No JUnit results produced; see output_tail" in errors


def test_stale_junit_from_an_earlier_run_is_not_read(gut: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    gut.RESULTS_XML.parent.mkdir(parents=True)
    gut.RESULTS_XML.write_text(fixture_text("gut-9.7.1-orphans.junit.xml"))
    _stub_run(gut, monkeypatch, None, ok=False, exit_code=1)

    result = gut.run_tests()

    assert result["passed"] == 0
    assert "No JUnit results produced; see output_tail" in result["errors"]


def test_no_tests_ran_is_not_ok(gut: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_run(gut, monkeypatch, '<testsuites name="GutTests" failures="0" tests="0" ></testsuites>')

    result = gut.run_tests()

    assert result["ok"] is False
    assert any(e.startswith("No tests ran") for e in result["errors"])


def test_orphans_fail_a_green_run(gut: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_run(gut, monkeypatch, fixture_text("gut-9.7.1-orphans.junit.xml"), orphans=3)

    result = gut.run_tests()

    assert result["passed"] == 3
    assert result["orphans"] == 3
    assert result["ok"] is False


def test_script_error_fails_a_green_run_that_exited_0(gut: ModuleType,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    error = "SCRIPT ERROR: Parse Error: x [res://tests/unit/test_broken.gd:5]"
    _stub_run(gut, monkeypatch, fixture_text("gut-9.7.1-orphans.junit.xml"), ok=False, errors=[error])

    result = gut.run_tests()

    assert result["ok"] is False
    assert error in result["errors"]


def test_plain_error_does_not_fail_a_green_run(gut: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # Settled in review-pr eval 001 #7 and the comment in _godot: GUT already turns an engine
    # ERROR raised during a test into that test's failure in the JUnit results.
    _stub_run(gut, monkeypatch, fixture_text("gut-9.7.1-orphans.junit.xml"), ok=False,
              errors=["ERROR: Condition \"!p_node\" is true."])

    result = gut.run_tests()

    assert result["ok"] is True
    assert result["errors"] == []


def test_script_selects_its_directory_and_file(gut: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_run(gut, monkeypatch, fixture_text("gut-9.7.1-orphans.junit.xml"))

    gut.run_tests(script="res://tests/unit/test_builder.gd", test_name="cash")

    args = calls[0]
    assert "-gdir=res://tests/unit" in args
    assert "-gselect=test_builder.gd" in args
    assert "-gunit_test_name=cash" in args
    assert "-gdir=res://tests" not in args


# --- 5. GUT missing ------------------------------------------------------------------------


def test_gut_missing_returns_the_full_result(mod: ModuleType) -> None:
    result = mod.run_tests()

    assert result["ok"] is False
    assert {"passed", "failed", "pending", "failures", "orphans", "exit_code"} <= set(result)


# --- 6. build ------------------------------------------------------------------------------


def test_export_without_presets_fails_with_a_full_step(mod: ModuleType,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_run(mod, monkeypatch)

    result = mod.build(export_preset="Linux")

    assert result["ok"] is False
    assert set(result["steps"]["export"]) == RUN_KEYS
    assert result["steps"]["export"]["ok"] is False


def test_only_failed_steps_keep_output_tail(mod: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(args: list[str], timeout: int, headless: bool = True) -> dict:
        if args == ["--import"]:
            return run_result(output_tail="imported")
        return run_result(ok=False, exit_code=1, errors=["SCRIPT ERROR: x"], output_tail="broken")

    monkeypatch.setattr(mod, "_godot", fake)

    steps = mod.build()["steps"]

    assert "output_tail" not in steps["import"]
    assert steps["check_scripts"]["output_tail"] == "broken"


def test_export_path_outside_the_project_is_refused(mod: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    (mod.ROOT / "export_presets.cfg").write_text("")
    _stub_run(mod, monkeypatch)

    with pytest.raises(ValueError, match="escapes project"):
        mod.build(export_preset="Linux", export_path="../outside/game")


# --- 7. find_scenes and scene_tree ---------------------------------------------------------

MAIN_TSCN = """\
[gd_scene load_steps=3 format=3 uid="uid://b0test"]

[ext_resource type="Script" path="res://scripts/main.gd" id="1_main"]
[ext_resource type="PackedScene" path="res://scenes/hud.tscn" id="2_hud"]

[node name="Main" type="Node3D"]
script = ExtResource("1_main")

[node name="World" type="Node3D" parent="."]

[node name="Grid" type="GridMap" parent="World"]

[node name="Cursor" type="Sprite3D" parent="World/Grid"]
text = "not a script line"

[node name="Hud" parent="." instance=ExtResource("2_hud")]
"""

HUD_TSCN = """\
[gd_scene format=3]

[node name="Hud" type="Control"]
"""

MAIN_NODES = [
    {"node_path": ".", "name": "Main", "type": "Node3D", "script": "res://scripts/main.gd", "instance": None},
    {"node_path": "World", "name": "World", "type": "Node3D", "script": None, "instance": None},
    {"node_path": "World/Grid", "name": "Grid", "type": "GridMap", "script": None, "instance": None},
    {"node_path": "World/Grid/Cursor", "name": "Cursor", "type": "Sprite3D", "script": None, "instance": None},
    {"node_path": "Hud", "name": "Hud", "type": None, "script": None, "instance": "res://scenes/hud.tscn"},
]


@pytest.fixture
def scenes(mod: ModuleType) -> ModuleType:
    """ROOT with scenes/main.tscn, scenes/hud.tscn, and scenes under addons/ and .godot/."""
    for rel, text in [("scenes/main.tscn", MAIN_TSCN), ("scenes/hud.tscn", HUD_TSCN),
                      ("addons/plugin/dock.tscn", HUD_TSCN), (".godot/editor/cache.tscn", HUD_TSCN)]:
        path = mod.ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return mod


def test_scene_tree_parses_paths_types_scripts_and_instances(scenes: ModuleType) -> None:
    assert scenes.scene_tree("res://scenes/main.tscn") == {"scene": "res://scenes/main.tscn",
                                                            "nodes": MAIN_NODES}


def test_find_scenes_without_query_lists_each_scene_with_its_root(scenes: ModuleType) -> None:
    assert scenes.find_scenes("") == [
        {"scene": "res://scenes/hud.tscn", "root_name": "Hud", "root_type": "Control", "script": None,
         "node_count": 1},
        {"scene": "res://scenes/main.tscn", "root_name": "Main", "root_type": "Node3D",
         "script": "res://scripts/main.gd", "node_count": 5},
    ]


@pytest.mark.parametrize(("query", "expected"), [
    pytest.param("world/grid/cursor", [("res://scenes/main.tscn", "World/Grid/Cursor")], id="node-path"),
    pytest.param("GRIDMAP", [("res://scenes/main.tscn", "World/Grid")], id="type"),
    pytest.param("Scripts/Main.gd", [("res://scenes/main.tscn", ".")], id="script"),
    pytest.param("HUD.TSCN", [("res://scenes/hud.tscn", "."), ("res://scenes/main.tscn", "Hud")],
                 id="instance-and-scene-path"),
    pytest.param("SCENES/MAIN", [("res://scenes/main.tscn", n["node_path"]) for n in MAIN_NODES],
                 id="scene-path"),
])
def test_find_scenes_matches_case_insensitively(scenes: ModuleType, query: str,
                                                expected: list[tuple[str, str]]) -> None:
    assert [(hit["scene"], hit["node_path"]) for hit in scenes.find_scenes(query)] == expected


@pytest.mark.parametrize("scene", ["res://scripts/main.gd", "res://scenes/missing.tscn"])
def test_scene_tree_of_a_non_scene_is_an_error(scenes: ModuleType, scene: str) -> None:
    (scenes.ROOT / "scripts").mkdir()
    (scenes.ROOT / "scripts/main.gd").write_text("extends Node3D\n")

    assert "error" in scenes.scene_tree(scene)


def test_scene_tree_outside_the_project_is_refused(scenes: ModuleType) -> None:
    (scenes.ROOT.parent / "outside.tscn").write_text(HUD_TSCN)

    with pytest.raises(ValueError, match="escapes project"):
        scenes.scene_tree("res://../outside.tscn")


# --- 8. Tools the skills call --------------------------------------------------------------


def test_tools_keep_the_names_and_parameters_skills_call(mod: ModuleType) -> None:
    # Skills and AGENTS.md call these as godot.<name>(<param>=...); a rename breaks them silently.
    tools = {t.name: set(t.input_schema["properties"]) for t in asyncio.run(mod.mcp.list_tools())}

    assert tools == {
        "build": {"export_preset", "export_path"},
        "run_tests": {"path", "test_name", "script"},
        "screenshot": {"scene", "width", "height", "state", "hover", "frames"},
        "find_scenes": {"query"},
        "scene_tree": {"scene"},
    }
