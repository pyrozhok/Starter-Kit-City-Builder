"""RUNS=<dir> python grade.py <run> ... (from uv run --with 'mcp>=2.3,<3'): suite on the agent's result, then each grading mutation applied on top of it.

A mutation is caught when at least one test the agent added fails on it. Prints one JSON line per run.
"""
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

RUNS = Path(os.environ.get("RUNS", "/tmp/write-test-004"))
BUILDER = "scripts/builder.gd"
PREV = '\tif Input.is_action_just_pressed("structure_previous"):'
DEMOLISH_SET = "\t\t\tgridmap.set_cell_item(gridmap_position, -1)\n"

# mutation id -> list of (old, new), each old must occur exactly once (or `count` given as 3rd item)
M = {
    "a1": [("wrap(index - 1, 0", "wrap(index + 1, 0")],
    "a2": [(PREV, '\tif false:')],
    "b1": [("if previous_tile != index:", "if true:")],
    "b2": [("if previous_tile != index:", "if false:")],
    "c1": [(DEMOLISH_SET, "\t\t\tpass\n")],
    "c2": [("set_cell_item(gridmap_position, -1)", "set_cell_item(gridmap_position, 1)")],
    "d0": [(' and not pointer_over_ui()', '', 2)],
    "d1": [('is_action_just_pressed("build") and not pointer_over_ui()', 'is_action_just_pressed("build")')],
    "d2": [('is_action_just_pressed("demolish") and not pointer_over_ui()', 'is_action_just_pressed("demolish")')],
    "e1": [("if previous_tile != index:", "if previous_tile == -1:")],
    "e2": [("if previous_tile != index:", "if false:")],
    "e3": [("map.cash -= structures[index].price", "map.cash -= structures[previous_tile].price")],
    "f1": [("deg_to_rad(90)", "deg_to_rad(-90)")],
    "f2": [("deg_to_rad(90)", "deg_to_rad(180)")],
    "f3": [("\t\tselector.rotate_y(deg_to_rad(90))\n", "\t\tpass\n")],
    "g1": [(DEMOLISH_SET, "\t\t\tmap.cash += structures[gridmap.get_cell_item(gridmap_position)].price\n\t\t\tupdate_cash()\n" + DEMOLISH_SET)],
    "g2": [(DEMOLISH_SET, "\t\t\tmap.cash += structures[gridmap.get_cell_item(gridmap_position)].price\n" + DEMOLISH_SET)],
    "h1": [("wrap(index + 1, 0, structures.size())", "wrap(index, 0, structures.size())")],
    # added in 004: the nearest wrong variant from tasks-003 (h), not one of its grading mutations
    "h3": [("wrap(index + 1, 0, structures.size())", "wrap(index - 1, 0, structures.size())")],
    "h2": [("\tif index != previous_index:\n\t\tupdate_structure()", "\tif index != previous_index:\n\t\tpass")],
}


def suite(run: Path) -> dict:
    spec = importlib.util.spec_from_file_location(f"g_{run.name}", run / "tools/mcp/godot_mcp.py")
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    return g.run_tests()


def failing(r: dict) -> set[str]:
    return {f["test"].split("::")[-1] for f in r.get("failures") or []}


def new_tests(run: Path) -> list[str]:
    diff = (RUNS / f"{run.name}.diff").read_text()
    return re.findall(r"^\+func (test_\w+)", diff, re.M)


def grade(name: str) -> dict:
    run = RUNS / name
    task = name.split("-")[1]
    b = run / BUILDER
    original = b.read_text()
    tests = new_tests(run)
    r = suite(run)
    out = {"run": name, "new_tests": tests, "ok": r.get("ok"), "passed": r.get("passed"), "failed": r.get("failed"),
           "orphans": r.get("orphans"), "errors": r.get("errors", [])[:3], "mutations": {}}
    if task == "h":
        tb = (run / "tests/unit/test_builder.gd").read_text()
        be = tb[tb.index("func before_each"):tb.index("func after_each")]
        out["set_process_after_tree"] = be.rfind("set_process(false)") > max(be.rfind("add_child(builder)"), be.rfind("add_child_autofree(builder)"))
    try:
        for mid, edits in M.items():
            if mid[0] != task:
                continue
            src = original
            for old, new, *count in edits:
                if src.count(old) != (count[0] if count else 1):
                    out["mutations"][mid] = f"NOT APPLIED: {old!r} x{src.count(old)}"
                    break
                src = src.replace(old, new)
            else:
                b.write_text(src)
                red = failing(suite(run)) & set(tests)
                out["mutations"][mid] = sorted(red) or "SURVIVED"
    finally:
        b.write_text(original)
    return out


if __name__ == "__main__":
    for n in sys.argv[1:]:
        print(json.dumps(grade(n)), flush=True)
