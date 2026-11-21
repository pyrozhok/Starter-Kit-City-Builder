"""Tests for tools/mcp/godot_mcp.py, the `godot` MCP server. Plan: issue #2. No Godot needed.

Godot is a separate process, and the tests treat it as one: `godot` (conftest.FakeGodot) is an
executable that replays real Godot 4.7.2 / GUT 9.7.1 runs (fixtures/README.md). Command lines are
pinned to the ones those runs used.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

# Keys of a finished Godot run (`_godot`); a run that never finished returns the same ones.
RUN_KEYS = {"ok", "exit_code", "errors", "output_tail", "orphans"}
NO_JUNIT = "No JUnit results produced; see output_tail"


def headless(mod: ModuleType, *args: str) -> list[str]:
    """A command line as godot_mcp passes it to a headless Godot (the binary left out)."""
    return ["--headless", "--path", str(mod.ROOT), *args]


# --- 1. _godot: running the process --------------------------------------------------------


def test_missing_binary_is_a_failure_without_exit_code(mod: ModuleType) -> None:
    result = mod._godot(["--version"], timeout=5)

    assert result["ok"] is False
    assert result["exit_code"] is None
    assert result["errors"] == [f"Godot binary not found: {mod.GODOT} (set GODOT_BIN)"]


def test_godot_runs_headless_in_the_project(mod: ModuleType, godot) -> None:
    godot.on()

    mod._godot(["--import"], timeout=5)

    assert godot.calls == [headless(mod, "--import")]


def test_timeout_keeps_what_godot_printed(mod: ModuleType, godot) -> None:
    godot.on(stderr="ERROR: still importing\n", sleep=30)

    result = mod._godot(["--import"], timeout=1)

    assert result["ok"] is False
    assert result["exit_code"] is None
    assert result["errors"][0] == f"Timed out after 1s: {mod.GODOT} {' '.join(headless(mod, '--import'))}"
    assert "still importing" in result["output_tail"]
    assert set(result) == RUN_KEYS


def test_run_that_never_finished_has_the_keys_of_a_finished_run(mod: ModuleType, godot) -> None:
    missing = mod._godot(["--import"], timeout=5)
    godot.on(stdout="done\n")
    finished = mod._godot(["--import"], timeout=5)

    assert set(finished) == RUN_KEYS
    assert set(missing) == RUN_KEYS


def test_ansi_codes_are_stripped(mod: ModuleType, godot) -> None:
    godot.on(stderr="\x1b[1;31mERROR: red text\x1b[0m\n")

    result = mod._godot([], timeout=5)

    assert result["errors"] == ["ERROR: red text"]
    assert "\x1b" not in result["output_tail"]


def test_at_line_is_appended_to_its_error(mod: ModuleType, godot) -> None:
    godot.on(capture="gut-9.7.1-mixed", code=1)

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


def test_output_that_is_not_utf8_does_not_break_the_run(mod: ModuleType, godot) -> None:
    # synthetic: no capture holds a byte that isn't UTF-8. Godot prints file names and strings a
    # script printed as they are; one such byte used to raise UnicodeDecodeError in every tool.
    godot.on(stderr="ERROR: Cannot open file 'caf\udce9.png'.\n", code=1)

    result = mod._godot([], timeout=5)

    assert result["errors"] == ["ERROR: Cannot open file 'caf\ufffd.png'."]


def test_duplicate_errors_are_collapsed(mod: ModuleType, godot) -> None:
    godot.on(stderr="ERROR: same\nERROR: same\nWARNING: other\nERROR: same\n")

    assert mod._godot([], timeout=5)["errors"] == ["ERROR: same", "WARNING: other"]


@pytest.mark.parametrize(("stderr", "ok"), [
    ("ERROR: Failed to load resource\n", False),
    ("SCRIPT ERROR: Parse Error: x\n", False),
    ("USER ERROR: boom\n", False),
    ("WARNING: 3 ObjectDB instances were leaked at exit\n", True),  # from the orphans capture
])
def test_ok_on_exit_0_depends_on_error_lines(mod: ModuleType, godot, stderr: str, ok: bool) -> None:
    godot.on(stderr=stderr, code=0)

    assert mod._godot([], timeout=5)["ok"] is ok


def test_nonzero_exit_is_not_ok(mod: ModuleType, godot) -> None:
    godot.on(code=1)

    result = mod._godot([], timeout=5)

    assert result["ok"] is False
    assert result["exit_code"] == 1


def test_output_tail_keeps_the_end_of_long_output(mod: ModuleType, godot) -> None:
    godot.on(stdout="".join(f"line {n}\n" for n in range(1000)), stderr="ERROR: the last word\n", code=1)

    tail = mod._godot([], timeout=5)["output_tail"]

    assert len(tail) <= 4000
    assert tail.endswith("ERROR: the last word\n")
    assert "line 0\n" not in tail


# --- 2. Orphan parsing ---------------------------------------------------------------------


def test_orphans_are_summed_over_test_scripts(mod: ModuleType, godot) -> None:
    godot.on(capture="gut-9.7.1-orphans")  # test_leak_a.gd leaked 1 node, test_leak_b.gd leaked 2

    assert mod._godot([], timeout=5)["orphans"] == 3


def test_per_test_and_summary_orphan_lines_are_not_counted(mod: ModuleType, godot) -> None:
    lines = godot.fixture("gut-9.7.1-orphans.stdout.txt").splitlines(keepends=True)
    # GUT writes the script-level line as "<n> orphans"; per-test and summary lines say "Orphans".
    script_lines = [line for line in lines if "orphans" in line]
    assert len(script_lines) == 2
    godot.on(stdout="".join(line for line in lines if line not in script_lines))

    assert mod._godot([], timeout=5)["orphans"] == 0


# --- 3. _git_snapshot and files_changed_by_build -------------------------------------------


@pytest.mark.parametrize(("before", "write", "delete", "expected"), [
    pytest.param({}, {}, (), [], id="nothing-on-clean-tree"),
    pytest.param({}, {"new.gd.uid": "uid://x\n"}, (), ["new.gd.uid"], id="creates-untracked"),
    pytest.param({}, {"tracked.txt": "b\n"}, (), ["tracked.txt"], id="rewrites-clean-tracked"),
    pytest.param({"dirty.txt": "b\n"}, {"dirty.txt": "c\n"}, (), ["dirty.txt"], id="changes-dirty-again"),
    pytest.param({"dirty.txt": "b\n"}, {"dirty.txt": "a\n"}, (), ["dirty.txt"], id="restores-dirty-to-head"),
    pytest.param({"untracked.txt": "x\n"}, {}, ("untracked.txt",), ["untracked.txt"], id="deletes-untracked"),
    pytest.param({"dirty.txt": "b\n"}, {}, (), [], id="leaves-dirty-alone"),
    pytest.param({"ignored.txt": "x\n"}, {"ignored.txt": "y\n"}, (), [], id="changes-ignored"),
])
def test_files_changed_by_build(mod: ModuleType, repo: Path, godot, before: dict[str, str],
                                write: dict[str, str], delete: tuple[str, ...], expected: list[str]) -> None:
    for name, text in before.items():
        (repo / name).write_text(text)
    godot.on("--import", write=write, delete=delete).on()

    assert mod.build()["files_changed_by_build"] == expected


@pytest.mark.parametrize(("write", "expected"), [
    pytest.param({"new.gd.uid": "uid://x\n"}, ["new.gd.uid"], id="creates-untracked"),
    pytest.param({"staged.txt": "b\n"}, ["staged.txt"], id="rewrites-staged"),
])
def test_files_changed_by_build_before_the_first_commit(mod: ModuleType, godot, write: dict[str, str],
                                                        expected: list[str]) -> None:
    # `git init` and `git add`, no commit yet: there is no HEAD for `git diff HEAD`.
    root: Path = mod.ROOT
    (root / "staged.txt").write_text("a\n")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "staged.txt"], cwd=root, check=True)
    godot.on("--import", write=write).on()

    assert mod.build()["files_changed_by_build"] == expected


def test_files_changed_by_build_is_empty_outside_a_git_repo(mod: ModuleType, godot) -> None:
    godot.on("--import", write={"new.gd.uid": "uid://x\n"}).on()

    assert mod.build()["files_changed_by_build"] == []


# --- 4. run_tests and JUnit parsing --------------------------------------------------------


@pytest.fixture
def gut(mod: ModuleType) -> ModuleType:
    """ROOT with GUT installed (only the file run_tests checks for)."""
    cmdln = mod.ROOT / "addons/gut/gut_cmdln.gd"
    cmdln.parent.mkdir(parents=True)
    cmdln.write_text("extends SceneTree\n")
    return mod


def gut_command(mod: ModuleType, *select: str) -> list[str]:
    # The command every capture in fixtures/ was taken with, against real Godot 4.7.2 / GUT 9.7.1.
    return headless(mod, "-s", "res://addons/gut/gut_cmdln.gd", "-gconfig=res://.gutconfig.json",
                    "-gexit", "-gjunit_xml_file=res://.godot/gut_results.xml", *select)


def test_run_tests_runs_gut_on_the_test_directory(gut: ModuleType, godot) -> None:
    godot.on(capture="gut-9.7.1-orphans")

    gut.run_tests()

    assert godot.calls == [gut_command(gut, "-gdir=res://tests")]


def test_script_selects_its_directory_and_file(gut: ModuleType, godot) -> None:
    godot.on(capture="gut-9.7.1-orphans")

    gut.run_tests(script="res://tests/unit/test_builder.gd", test_name="cash")

    assert godot.calls == [gut_command(gut, "-gdir=res://tests/unit", "-gselect=test_builder.gd",
                                       "-gunit_test_name=cash")]


def test_passed_failed_and_pending_are_counted(gut: ModuleType, godot) -> None:
    godot.on(capture="gut-9.7.1-mixed", code=1)

    result = gut.run_tests()

    assert (result["passed"], result["failed"], result["pending"]) == (1, 1, 1)
    assert result["failures"] == [{
        "test": "tests/mixed/test_mixed.gd::test_fails",
        "message": "[2] expected to equal [3]: two is not three at line 9",
    }]
    assert result["ok"] is False
    assert "two is not three" in result["output_tail"]


def test_green_run_is_ok_and_terse(gut: ModuleType, godot) -> None:
    # The skipped-script run as it would be without test_broken.gd: same JUnit, nothing on stderr.
    godot.on(junit=godot.fixture("gut-9.7.1-skipped-script.junit.xml"), stdout="1/1 passed.\n")

    result = gut.run_tests()

    assert result == {"ok": True, "passed": 1, "failed": 0, "pending": 0, "failures": [], "orphans": 0,
                      "errors": [], "exit_code": 0}


def test_failure_without_body_falls_back_to_message(gut: ModuleType, godot) -> None:
    # GUT 9.7.1 always fills the body (see the mixed capture); this pins the fallback, not a real run.
    junit = ('<testsuites><testsuite name="t"><testcase name="test_x" classname="tests/t.gd">'
             '<failure message="boom"/></testcase></testsuite></testsuites>')
    godot.on(junit=junit, code=1)

    assert gut.run_tests()["failures"] == [{"test": "tests/t.gd::test_x", "message": "boom"}]


def test_truncated_junit_is_reported_as_missing(gut: ModuleType, godot) -> None:
    junit = godot.fixture("gut-9.7.1-mixed.junit.xml")
    godot.on(junit=junit[: len(junit) // 2], code=1)

    result = gut.run_tests()

    assert result["ok"] is False
    assert NO_JUNIT in result["errors"]


def test_no_junit_reports_godot_errors_and_the_missing_file(gut: ModuleType, godot) -> None:
    godot.on(stderr="ERROR: boom\n", code=1)

    errors = gut.run_tests()["errors"]

    assert "ERROR: boom" in errors
    assert NO_JUNIT in errors


def test_stale_junit_from_an_earlier_run_is_not_read(gut: ModuleType, godot) -> None:
    gut.RESULTS_XML.parent.mkdir(parents=True)
    gut.RESULTS_XML.write_text(godot.fixture("gut-9.7.1-orphans.junit.xml"))
    godot.on(code=1)

    result = gut.run_tests()

    assert result["passed"] == 0
    assert NO_JUNIT in result["errors"]


def test_nothing_ran_is_not_ok(gut: ModuleType, godot) -> None:
    godot.on(capture="gut-9.7.1-nothing-ran", code=0)

    result = gut.run_tests()

    assert result["ok"] is False
    assert result["errors"] == ["No tests ran (bad path/test_name, or test scripts failed to load)"]


def test_orphans_fail_a_green_run(gut: ModuleType, godot) -> None:
    godot.on(capture="gut-9.7.1-orphans", code=0)

    result = gut.run_tests()

    assert (result["passed"], result["failed"], result["orphans"]) == (3, 0, 3)
    assert result["ok"] is False


def test_skipped_script_fails_a_run_that_exited_0(gut: ModuleType, godot) -> None:
    # GUT skips a test script that doesn't parse, runs the rest and exits 0.
    godot.on(capture="gut-9.7.1-skipped-script", code=0)

    result = gut.run_tests()

    assert (result["passed"], result["exit_code"]) == (1, 0)
    assert result["ok"] is False
    assert result["errors"] == [
        'SCRIPT ERROR: Parse Error: Cannot assign a value of type "String" as "int". '
        "[res://tests/skip/test_broken.gd:5]",
        'SCRIPT ERROR: Parse Error: Cannot assign a value of type String to variable "x" with '
        "specified type int. [res://tests/skip/test_broken.gd:5]",
    ]


def test_engine_error_in_a_test_counts_once(gut: ModuleType, godot) -> None:
    # Settled in review-pr eval 001 #7 and the comment in _godot: GUT turns an engine ERROR during
    # a test into that test's failure, so the ERROR line isn't counted again on top.
    godot.on(capture="gut-9.7.1-push-error", code=1)

    result = gut.run_tests()

    assert (result["passed"], result["failed"]) == (0, 1)
    assert result["failures"][0]["message"].startswith("Unexpected Errors: [1] <push_error>boom from the test")
    assert result["errors"] == []


# --- 5. GUT missing ------------------------------------------------------------------------


def test_gut_missing_returns_the_full_result_without_running_godot(mod: ModuleType, godot) -> None:
    godot.on(capture="gut-9.7.1-orphans")

    result = mod.run_tests()

    assert result == {"ok": False, "exit_code": None, "errors": ["GUT not installed at addons/gut"],
                      "output_tail": "", "orphans": 0, "passed": 0, "failed": 0, "pending": 0,
                      "failures": []}
    assert godot.calls == []


# --- 6. build ------------------------------------------------------------------------------


def test_build_imports_then_checks_scripts(mod: ModuleType, godot) -> None:
    godot.on()

    result = mod.build()

    # Both commands were run against real Godot 4.7.2 on this project when the suite was written.
    assert godot.calls == [headless(mod, "--import"), headless(mod, "-s", "res://tools/mcp/check_scripts.gd")]
    assert result["ok"] is True
    assert set(result["steps"]) == {"import", "check_scripts"}


def test_only_failed_steps_keep_output_tail(mod: ModuleType, godot) -> None:
    godot.on("res://tools/mcp/check_scripts.gd", code=1,
             stderr="SCRIPT ERROR: Parse Error: x\n   at: GDScript::reload (res://scripts/x.gd:3)\n")
    godot.on(stdout="imported\n")

    result = mod.build()

    assert "output_tail" not in result["steps"]["import"]
    assert "Parse Error" in result["steps"]["check_scripts"]["output_tail"]
    assert result["ok"] is False


def test_export_without_presets_fails_with_a_full_step(mod: ModuleType, godot) -> None:
    godot.on()

    result = mod.build(export_preset="Linux")

    assert result["ok"] is False
    assert set(result["steps"]["export"]) == RUN_KEYS
    assert result["steps"]["export"]["errors"][0].startswith("export_presets.cfg missing")
    assert len(godot.calls) == 2  # import and check_scripts; no export attempted


@pytest.mark.parametrize(("export_path", "out"), [(None, "build/Linux"), ("res://dist/linux/game.x86_64", "dist/linux/game.x86_64")])
def test_export_writes_the_preset_to_its_path(mod: ModuleType, godot, export_path: str | None, out: str) -> None:
    (mod.ROOT / "export_presets.cfg").write_text("")
    godot.on()

    result = mod.build(export_preset="Linux", export_path=export_path)

    # Godot CLI: --export-release <preset> <path>.
    assert godot.calls[2] == headless(mod, "--export-release", "Linux", str(mod.ROOT / out))
    assert (mod.ROOT / out).parent.is_dir()
    assert result["ok"] is True
    assert "output_tail" not in result["steps"]["export"]


def test_export_again_into_an_existing_directory(mod: ModuleType, godot) -> None:
    (mod.ROOT / "export_presets.cfg").write_text("")
    godot.on()

    first = mod.build(export_preset="Linux")
    second = mod.build(export_preset="Linux")

    assert (first["ok"], second["ok"]) == (True, True)


def test_export_path_outside_the_project_is_refused(mod: ModuleType, godot) -> None:
    (mod.ROOT / "export_presets.cfg").write_text("")
    godot.on()

    with pytest.raises(Exception, match="escapes project"):
        mod.build(export_preset="Linux", export_path="../outside/game")
    assert len(godot.calls) == 2


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


def test_built_in_script_is_reported_as_written(scenes: ModuleType) -> None:
    # A script saved inside the scene is a SubResource, not a file.
    (scenes.ROOT / "scenes/builtin.tscn").write_text(
        '[gd_scene format=3]\n\n[sub_resource type="GDScript" id="GDScript_k2x"]\n'
        'script/source = "extends Node"\n\n[node name="Root" type="Node"]\nscript = SubResource("GDScript_k2x")\n')

    assert scenes.scene_tree("res://scenes/builtin.tscn")["nodes"][0]["script"] == 'SubResource("GDScript_k2x")'


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

    assert scenes.scene_tree(scene) == {"error": f"Not a .tscn scene: {scene}"}


def test_scene_tree_outside_the_project_is_refused(scenes: ModuleType) -> None:
    (scenes.ROOT.parent / "outside.tscn").write_text(HUD_TSCN)

    with pytest.raises(Exception, match="escapes project"):
        scenes.scene_tree("res://../outside.tscn")


# --- 8. Tools the skills call --------------------------------------------------------------

# Parameters the skills pass, per tool (`.claude/skills/*/SKILL.md`, `generate-ui/mockup.md`).
SKILL_CALLS = {
    "build": set(),                                                   # review-pr, generate-ui
    "run_tests": {"script", "test_name"},                             # write-test
    "screenshot": {"scene", "width", "height", "state", "hover"},     # generate-ui/mockup.md
    "scene_tree": {"scene"},                                          # generate-ui
    "find_scenes": {"query"},                                         # generate-ui
}


@pytest.mark.parametrize("tool", sorted(SKILL_CALLS))
def test_skills_can_still_call_the_tool(mod: ModuleType, tool: str) -> None:
    # Breaking for a skill: the tool or a parameter it passes is gone, or a new parameter is required.
    # Adding an optional parameter is not.
    tools = {t.name: t.input_schema for t in asyncio.run(mod.mcp.list_tools())}

    assert tool in tools
    assert SKILL_CALLS[tool] <= set(tools[tool]["properties"])
    assert set(tools[tool].get("required", [])) <= SKILL_CALLS[tool]


# --- 9. Over MCP: what the agent receives --------------------------------------------------


def call(mod: ModuleType, tool: str, arguments: dict):
    """Call a tool the way an agent does: an MCP client session to the server, in memory."""
    from mcp.client import Client

    async def run():
        async with Client(mod.mcp) as client:
            return await client.call_tool(tool, arguments)

    return asyncio.run(run())


def test_results_reach_the_client_as_json(scenes: ModuleType) -> None:
    tree = call(scenes, "scene_tree", {"scene": "res://scenes/main.tscn"})
    found = call(scenes, "find_scenes", {"query": "gridmap"})

    assert tree.is_error is False
    assert json.loads(tree.content[0].text) == {"scene": "res://scenes/main.tscn", "nodes": MAIN_NODES}
    assert found.structured_content == {"result": [{"scene": "res://scenes/main.tscn", **MAIN_NODES[2]}]}


def test_run_tests_over_mcp_reports_the_failing_test(gut: ModuleType, godot) -> None:
    # Agent → MCP session → run_tests → Godot process → JUnit file → result.
    godot.on(capture="gut-9.7.1-mixed", code=1)

    result = call(gut, "run_tests", {"script": "res://tests/mixed/test_mixed.gd"})

    body = json.loads(result.content[0].text)
    assert (body["ok"], body["failed"]) == (False, 1)
    assert body["failures"][0]["test"] == "tests/mixed/test_mixed.gd::test_fails"


def test_refused_path_tells_the_agent_why(scenes: ModuleType) -> None:
    result = call(scenes, "scene_tree", {"scene": "res://../outside.tscn"})

    assert result.is_error is True
    assert "Path escapes project: res://../outside.tscn" in result.content[0].text


# --- 10. screenshot ------------------------------------------------------------------------


def shot_command(mod: ModuleType, *user_args: str) -> list[str]:
    # The command the screenshot captures were taken with, against a windowed Godot 4.7.2.
    return ["--path", str(mod.ROOT), "--audio-driver", "Dummy", "--resolution", "320x180",
            "-s", "res://tools/mcp/screenshot.gd", "--", *user_args]


def test_screenshot_runs_a_windowed_godot_with_its_arguments(scenes: ModuleType, godot) -> None:
    godot.on(capture="screenshot-4.7.2-ok")

    result = scenes.screenshot("res://scenes/main.tscn", state="save", hover="Root/New Game")

    out = scenes.ROOT / ".godot/screenshots/main_save_hover-New-Game.png"
    assert godot.calls == [shot_command(scenes, "--scene=res://scenes/main.tscn", f"--out={out}",
                                        "--size=1920x1080", "--frames=30", "--state=save",
                                        "--hover=Root/New Game")]
    assert (result["path"], result["layout_path"]) == (str(out), str(out.with_suffix(".layout.json")))


@pytest.mark.parametrize("scene", ["res://scenes/main.tscn", "res://scenes/main.scn"])
def test_screenshot_without_state_or_hover(scenes: ModuleType, godot, scene: str) -> None:
    (scenes.ROOT / "scenes/main.scn").write_bytes(b"RSCC")  # a binary scene: only its suffix matters here
    godot.on(capture="screenshot-4.7.2-ok")

    scenes.screenshot(scene, width=640, height=360, frames=5)

    out = scenes.ROOT / ".godot/screenshots/main.png"
    assert godot.calls == [shot_command(scenes, f"--scene={scene}", f"--out={out}", "--size=640x360",
                                        "--frames=5")]


def test_screenshot_keeps_machine_noise_apart(scenes: ModuleType, godot) -> None:
    # A real successful run: the exit-time messages name no res:// path, so they are the machine's.
    godot.on(capture="screenshot-4.7.2-ok")

    result = scenes.screenshot("res://scenes/main.tscn", state="save")

    assert (result["ok"], result["blank"], result["errors"]) == (True, False, [])
    assert result["environment_errors"] == [
        "WARNING: 4 ObjectDB instances were leaked at exit (run with `--verbose` for details).",
        "ERROR: 2 resources still in use at exit (run with --verbose for details).",
    ]
    assert "output_tail" not in result


def test_blank_frame_is_not_ok(scenes: ModuleType, godot) -> None:
    godot.on(capture="screenshot-4.7.2-blank")

    result = scenes.screenshot("res://scenes/main.tscn")

    assert (result["ok"], result["blank"]) == (False, True)
    assert "SCREENSHOT" in result["output_tail"]


def test_script_error_in_the_scene_fails_the_screenshot(scenes: ModuleType, godot) -> None:
    # Real run: _ready() calls a method on null; Godot still renders a frame and exits 0.
    godot.on(capture="screenshot-4.7.2-script-error")

    result = scenes.screenshot("res://scenes/main.tscn")

    assert (result["ok"], result["blank"]) == (False, False)
    assert result["errors"] == [
        "SCRIPT ERROR: Cannot call method 'queue_free' on a null value. [res://scripts/broken_ready.gd:6]"]


def test_scene_push_warning_is_reported_without_failing(scenes: ModuleType, godot) -> None:
    # Real run: _ready() calls push_warning(). Godot 4.7 names only the engine on the `at:` line;
    # the script is the first frame of the GDScript backtrace.
    godot.on(capture="screenshot-4.7.2-push-warning")

    result = scenes.screenshot("res://scenes/main.tscn")

    assert result["ok"] is True
    assert result["errors"] == ["WARNING: the scene warns [res://scripts/pw.gd:5]"]
    assert result["environment_errors"] == []


def test_scene_push_error_fails_the_screenshot(scenes: ModuleType, godot) -> None:
    # Real run: _ready() calls push_error(), printed as a plain ERROR, located by the backtrace.
    godot.on(capture="screenshot-4.7.2-push-error")

    result = scenes.screenshot("res://scenes/main.tscn")

    assert result["ok"] is False
    assert result["errors"] == ["ERROR: the scene says no [res://scripts/pe.gd:5]"]


def test_error_repeated_every_frame_is_reported_once(scenes: ModuleType, godot) -> None:
    # Real run: push_error() in _process() for three frames.
    godot.on(capture="screenshot-4.7.2-repeated-error")

    assert scenes.screenshot("res://scenes/main.tscn")["errors"] == ["ERROR: every frame [res://scripts/re.gd:9]"]


def test_shader_built_in_code_is_located_by_its_script(scenes: ModuleType, godot) -> None:
    # Real run: a script sets Shader.code with an unknown identifier. The `at:` line has no
    # res:// path (`(null) (:3)`); the backtrace names the script that set the code.
    godot.on(capture="screenshot-4.7.2-code-shader-error")

    result = scenes.screenshot("res://scenes/main.tscn")

    assert result["ok"] is False
    assert result["errors"] == [
        "SHADER ERROR: Unknown identifier in expression: 'nope'. [res://scripts/cs.gd:8]",
        "ERROR: Shader compilation failed. [res://scripts/cs.gd:8]",
    ]
    assert result["environment_errors"] == ['ERROR: Parameter "version" is null.']


def test_shader_in_a_scene_is_located_by_the_scene(scenes: ModuleType, godot) -> None:
    # Real run: a Shader sub-resource in a .tscn, no script. The backtrace holds only
    # screenshot.gd, which locates nothing in the project.
    godot.on(capture="screenshot-4.7.2-builtin-shader-error")

    result = scenes.screenshot("res://scenes/main.tscn")

    assert result["ok"] is False
    assert result["errors"] == ["SHADER ERROR: Unknown identifier in expression: 'nope'. [res://scenes/bs.tscn::Shader_bad:3]"]
    assert result["environment_errors"] == ["ERROR: Shader compilation failed.", 'ERROR: Parameter "version" is null.']


def test_shader_error_fails_the_screenshot(scenes: ModuleType, godot) -> None:
    # Real run with an unknown identifier in scenes/ui/backdrop_blur.gdshader: the frame renders.
    godot.on(capture="screenshot-4.7.2-shader-error")

    result = scenes.screenshot("res://scenes/main.tscn")

    assert result["ok"] is False
    assert ("SHADER ERROR: Unknown identifier in expression: 'undefined_thing'. "
            "[res://scenes/ui/backdrop_blur.gdshader:12]") in result["errors"]


def test_failed_screenshot_says_why(scenes: ModuleType, godot) -> None:
    # Real run with --hover naming no node: screenshot.gd prints the reason and exits 1.
    godot.on(capture="screenshot-4.7.2-hover-missing", code=1)

    result = scenes.screenshot("res://scenes/main.tscn", hover="Nope")

    assert (result["ok"], result["path"]) == (False, None)
    assert result["errors"][0] == "SCREENSHOT FAILED: hover target not found or not a Control: Nope"
    assert "SCREENSHOT FAILED" in result["output_tail"]


def test_silent_failure_still_has_an_error(scenes: ModuleType, godot) -> None:
    godot.on(code=1)  # no frame, nothing printed

    assert scenes.screenshot("res://scenes/main.tscn")["errors"] == ["No screenshot produced"]


def test_previous_screenshot_is_not_reported(scenes: ModuleType, godot) -> None:
    out = scenes.ROOT / ".godot/screenshots/main.png"
    out.parent.mkdir(parents=True)
    out.write_bytes(b"old")
    out.with_suffix(".layout.json").write_text('{"blank": false}')
    godot.on(capture="screenshot-4.7.2-hover-missing", code=1)

    assert scenes.screenshot("res://scenes/main.tscn")["path"] is None


@pytest.mark.parametrize("scene", ["res://scripts/main.gd", "res://scenes/missing.tscn"])
def test_screenshot_of_a_non_scene_runs_no_godot(scenes: ModuleType, godot, scene: str) -> None:
    (scenes.ROOT / "scripts").mkdir()
    (scenes.ROOT / "scripts/main.gd").write_text("extends Node3D\n")
    godot.on(capture="screenshot-4.7.2-ok")

    result = scenes.screenshot(scene)

    assert (result["ok"], result["path"], result["errors"]) == (False, None, [f"Not a scene: {scene}"])
    assert godot.calls == []


# --- 11. Real Godot, where one is installed ------------------------------------------------
# Everything above pins command lines to runs made by hand. These re-run them on a real Godot 4.7
# (GODOT_BIN or `godot` on PATH) in a minimal project; skipped without one, e.g. in CI.


def _real_godot() -> str | None:
    binary = shutil.which(os.environ.get("GODOT_BIN", "godot"))
    if not binary:
        return None
    try:
        version = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    return binary if version.startswith("4.7.") else None


REAL_GODOT = _real_godot()
REPO = Path(__file__).resolve().parents[3]


@pytest.mark.skipif(REAL_GODOT is None, reason="needs Godot 4.7: GODOT_BIN or godot on PATH")
def test_real_godot_builds_and_runs_gut(mod: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root: Path = mod.ROOT
    shutil.copytree(REPO / "addons/gut", root / "addons/gut")
    shutil.copy(REPO / ".gutconfig.json", root)
    (root / "tools/mcp").mkdir(parents=True)
    shutil.copy(REPO / "tools/mcp/check_scripts.gd", root / "tools/mcp")
    (root / "project.godot").write_text(
        'config_version=5\n\n[application]\n\nconfig/name="pytest"\nconfig/features=PackedStringArray("4.7")\n')
    (root / "tests").mkdir()
    (root / "tests/test_real.gd").write_text(
        "extends GutTest\n\n\nfunc test_passes() -> void:\n\tassert_eq(1, 1)\n\n\n"
        "func test_fails() -> void:\n\tassert_eq(2, 3, \"a real failure\")\n")
    for var in ("XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME"):  # Godot's user:// and caches
        monkeypatch.setenv(var, str(tmp_path / var.lower()))
    mod.GODOT = REAL_GODOT

    build = mod.build()
    result = mod.run_tests()

    assert build["ok"] is True, build
    assert (result["passed"], result["failed"], result["orphans"]) == (1, 1, 0), result
    assert result["failures"][0]["test"] == "tests/test_real.gd::test_fails"
    assert "a real failure" in result["failures"][0]["message"]
