# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=2.3,<3"]
# ///
"""MCP server for this Godot project: build (import + script check), GUT tests, scene search, screenshots.

Run: uv run --script tools/mcp/godot_mcp.py   (registered in .mcp.json)
Env: GODOT_BIN — Godot executable (default "godot"). Use the version the project targets.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

ROOT = Path(__file__).resolve().parents[2]
GODOT = os.environ.get("GODOT_BIN", "godot")
SKIP_DIRS = {".godot", "addons", ".git"}
RESULTS_XML = ROOT / ".godot" / "gut_results.xml"

mcp = MCPServer("godot")

# Godot prints e.g. "SCRIPT ERROR: Parse Error: ..." followed by "   at: GDScript::reload (res://x.gd:12)".
# SHADER ERROR comes only from a renderer (screenshot); headless runs never compile shaders.
_ERR_RE = re.compile(r"^(SCRIPT ERROR|SHADER ERROR|ERROR|WARNING|USER ERROR|USER WARNING):\s*(.*)$")
_AT_RE = re.compile(r"^\s+at:\s.*?\((res://[^)]+)\)")
# A GDScript backtrace frame, e.g. "       [0] _ready (res://scripts/x.gd:5)". push_error(), push_warning()
# and engine errors raised from a script name the engine on their `at:` line; the script is here.
_FRAME_RE = re.compile(r"^\s+\[\d+\] .*?\((res://[^)]+)\)")
# Frames of the harness that runs the project (this tool's scripts, GUT) locate nothing in it.
_HARNESS = ("res://tools/mcp/", "res://addons/gut/")
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
# GUT prints "<n> orphans" after each test script that leaked nodes (never printed when 0).
_ORPHANS_RE = re.compile(r"^(\d+) orphans$", re.MULTILINE)


def _failure(error: str, tail: str = "") -> dict:
    """Result of a Godot run that never finished; same keys as a finished run."""
    return {"ok": False, "exit_code": None, "errors": [error], "output_tail": tail, "orphans": 0}


def _godot(args: list[str], timeout: int, headless: bool = True) -> dict:
    cmd = [GODOT, *(["--headless"] if headless else []), "--path", str(ROOT), *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    except FileNotFoundError:
        return _failure(f"Godot binary not found: {GODOT} (set GODOT_BIN)")
    except subprocess.TimeoutExpired as e:
        out = _ANSI_RE.sub("", _text(e.stdout) + _text(e.stderr))
        return _failure(f"Timed out after {timeout}s: {' '.join(cmd)}", out[-4000:])
    output = _ANSI_RE.sub("", proc.stdout + proc.stderr)
    errors = _parse_errors(output)
    return {
        # Fatal for build: any engine ERROR (broken import, missing resource). run_tests uses a
        # narrower tuple on purpose: GUT turns an engine ERROR raised during a test into that
        # test's failure, already counted from the JUnit results, so there only SCRIPT/USER ERROR
        # (scripts GUT skipped as unloadable) count on top.
        "ok": proc.returncode == 0 and not any(e.startswith(("SCRIPT ERROR", "SHADER ERROR", "ERROR", "USER ERROR")) for e in errors),
        "exit_code": proc.returncode,
        "errors": errors,
        "output_tail": output[-4000:],
        "orphans": sum(int(n) for n in _ORPHANS_RE.findall(output)),
    }


def _text(stream: str | bytes | None) -> str:
    return stream.decode(errors="replace") if isinstance(stream, bytes) else (stream or "")


def _parse_errors(output: str) -> list[str]:
    errors: list[str] = []
    located = True  # errors[-1] has its res:// location, or there is no error yet
    for line in output.splitlines():
        m = _ERR_RE.match(line)
        if m:
            errors.append(f"{m.group(1)}: {m.group(2)}")
            located = False
            continue
        if located:
            continue
        at = _AT_RE.match(line)
        frame = _FRAME_RE.match(line)
        if at or (frame and not frame.group(1).startswith(_HARNESS)):
            errors[-1] += f" [{(at or frame).group(1)}]"
            located = True
    return list(dict.fromkeys(errors))


def _git_snapshot() -> dict[str, str]:
    """Hash of every modified tracked file and every untracked (not ignored) file.

    Comparing two snapshots catches files the build created (new .uid/.import), files it
    rewrote that were clean, and files that were already dirty but changed again.
    Empty if not a git repo.
    """
    cmds = (["git", "diff", "--name-only", "HEAD"], ["git", "ls-files", "--others", "--exclude-standard"])
    names: set[str] = set()
    for cmd in cmds:
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=30)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return {}
        if out.returncode != 0:
            return {}
        names.update(out.stdout.splitlines())
    snap: dict[str, str] = {}
    for name in names:
        f = ROOT / name
        snap[name] = hashlib.sha1(f.read_bytes()).hexdigest() if f.is_file() else "<deleted>"
    return snap


def _iter_files(suffix: str):
    for path in sorted(ROOT.rglob(f"*{suffix}")):
        rel = path.relative_to(ROOT)
        if not SKIP_DIRS.intersection(rel.parts):
            yield path


def _res(path: Path) -> str:
    return "res://" + path.relative_to(ROOT).as_posix()


def _to_path(res_path: str) -> Path:
    p = ROOT / res_path.removeprefix("res://")
    if not p.resolve().is_relative_to(ROOT):
        # ToolError, not ValueError: the MCP server passes only a ToolError's message on to the agent.
        raise ToolError(f"Path escapes project: {res_path}")
    return p


@mcp.tool()
def build(export_preset: str | None = None, export_path: str | None = None) -> dict:
    """Build the project: reimport assets, then compile every project GDScript (addons excluded)
    with autoloads loaded (tools/mcp/check_scripts.gd).

    If export_preset is given, also export with that preset (needs export_presets.cfg and
    installed export templates) to export_path (res:// or project-relative, default build/<preset>).
    `files_changed_by_build` lists files the run created or rewrote (tracked or untracked, not
    ignored), e.g. new .uid files, or .import/project.godot upgrades when GODOT_BIN is a newer
    Godot than the project targets.
    """
    before = _git_snapshot()
    steps: dict = {"import": _godot(["--import"], timeout=600)}
    steps["check_scripts"] = _godot(["-s", "res://tools/mcp/check_scripts.gd"], timeout=300)

    if export_preset:
        if not (ROOT / "export_presets.cfg").exists():
            steps["export"] = _failure("export_presets.cfg missing: create a preset in the editor (Project > Export).")
        else:
            out = _to_path(export_path or f"build/{export_preset}")
            out.parent.mkdir(parents=True, exist_ok=True)
            steps["export"] = _godot(["--export-release", export_preset, str(out)], timeout=1200)

    for step in steps.values():  # keep successful steps terse
        if step.get("ok"):
            step.pop("output_tail", None)
    after = _git_snapshot()
    return {
        "ok": all(s["ok"] for s in steps.values()),
        # Union, not just the after snapshot: a dirty file the build restored to HEAD, or an
        # untracked file it deleted, is gone from the after listing but still changed.
        "files_changed_by_build": sorted(n for n in before.keys() | after.keys() if before.get(n) != after.get(n)),
        "steps": steps,
    }


@mcp.tool()
def run_tests(path: str = "res://tests", test_name: str | None = None, script: str | None = None) -> dict:
    """Run GUT tests headless. path: test dir; script: single test file (res://...);
    test_name: only tests whose name contains this. Returns pass/fail counts, failures and orphans
    (nodes tests left unfreed; any orphan fails the run)."""
    if not (ROOT / "addons/gut/gut_cmdln.gd").exists():
        return {**_failure("GUT not installed at addons/gut"), "passed": 0, "failed": 0, "pending": 0, "failures": []}
    RESULTS_XML.unlink(missing_ok=True)
    args = ["-s", "res://addons/gut/gut_cmdln.gd", "-gconfig=res://.gutconfig.json", "-gexit",
            f"-gjunit_xml_file={_res(RESULTS_XML)}"]
    if script:  # -gtest would still run the .gutconfig dirs; -gselect filters by file name
        p = _to_path(script)
        args += [f"-gdir={_res(p.parent)}", f"-gselect={p.name}"]
    else:
        args.append(f"-gdir={path}")
    if test_name:
        args.append(f"-gunit_test_name={test_name}")
    run = _godot(args, timeout=900)

    summary = {"passed": 0, "failed": 0, "pending": 0, "failures": []}
    try:
        cases = list(ET.parse(RESULTS_XML).iter("testcase")) if RESULTS_XML.exists() else None
    except ET.ParseError:  # truncated file, e.g. Godot killed mid-write
        cases = None
    if cases is not None:
        for case in cases:
            name = f"{case.get('classname')}::{case.get('name')}"
            failure = case.find("failure")
            if failure is not None:
                summary["failed"] += 1
                # GUT puts the assertion text in the body; the message attribute is just "failed".
                text = " ".join((failure.text or failure.get("message") or "").split())
                summary["failures"].append({"test": name, "message": text})
            elif case.find("skipped") is not None:
                summary["pending"] += 1
            else:
                summary["passed"] += 1
    else:
        summary["errors"] = run["errors"] + ["No JUnit results produced; see output_tail"]

    # GUT exits 0 even when a test script fails to parse (it is just skipped), so script errors
    # and "nothing ran" both count as failure. Not _godot's tuple: a plain ERROR during a test
    # already fails that test in the JUnit results (see _godot).
    script_errors = [e for e in run["errors"] if e.startswith(("SCRIPT ERROR", "USER ERROR"))]
    ran = summary["passed"] + summary["failed"]
    if not ran:
        script_errors.append("No tests ran (bad path/test_name, or test scripts failed to load)")
    ok = run["exit_code"] == 0 and summary["failed"] == 0 and not run["orphans"] and not script_errors
    result = {"ok": ok, **summary, "orphans": run["orphans"], "errors": summary.get("errors", []) + script_errors, "exit_code": run["exit_code"]}
    if not ok:
        result["output_tail"] = run["output_tail"]
    return result


SCREENSHOTS = ROOT / ".godot" / "screenshots"


@mcp.tool()
def screenshot(scene: str, width: int = 1920, height: int = 1080, state: str | None = None,
               hover: str | None = None, frames: int = 30) -> dict:
    """Render a scene in a real (windowed, not headless) Godot and save one frame as PNG.

    The scene runs inside a SubViewport of exactly width×height, so the window size doesn't matter.
    state: passed to the scene root's `_preview_state(state)` (e.g. "save" / "nosave" for the menu).
    hover: Control path from the scene root to put the mouse over before the frame is taken.
    frames: frames to wait before capturing (map loads, tweens).
    Saves .godot/screenshots/<scene>[_<state>][_hover-<node>].png and, next to it, .layout.json with
    the viewport rect, class and theme variation of every visible Control.
    Returns path, layout_path, blank (true if the sampled pixels are all one colour), errors (project:
    res:// paths, SCRIPT/USER ERROR) and environment_errors (driver/display messages; never fail the run).
    Needs a display (Wayland/X11); a window opens for a few seconds.
    """
    path = _to_path(scene)
    if path.suffix not in (".tscn", ".scn") or not path.exists():
        return {**_failure(f"Not a scene: {scene}"), "path": None}
    name = path.stem + (f"_{state}" if state else "") + (f"_hover-{hover.rsplit('/', 1)[-1]}" if hover else "")
    out = SCREENSHOTS / f"{re.sub(r'[^A-Za-z0-9_.-]', '-', name)}.png"
    layout = out.with_suffix(".layout.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    layout.unlink(missing_ok=True)
    user_args = [f"--scene={_res(path)}", f"--out={out}", f"--size={width}x{height}", f"--frames={frames}"]
    if state:
        user_args.append(f"--state={state}")
    if hover:
        user_args.append(f"--hover={hover}")
    run = _godot(["--audio-driver", "Dummy", "--resolution", "320x180",
                  "-s", "res://tools/mcp/screenshot.gd", "--", *user_args], timeout=180, headless=False)
    if not out.exists() or not layout.exists():
        # screenshot.gd prints its own reason ("SCREENSHOT FAILED: ...") without an error prefix.
        reasons = re.findall(r"^SCREENSHOT FAILED: .*$", run["output_tail"], re.MULTILINE)
        return {"ok": False, "path": None, "errors": reasons + run["errors"] or ["No screenshot produced"],
                "output_tail": run["output_tail"]}
    blank = json.loads(layout.read_text())["blank"]
    # A windowed run logs driver/display noise (Vulkan, Wayland, portals) as plain ERROR without a
    # res:// path. That is the machine, not the project: report it apart and don't fail on it.
    project = [e for e in run["errors"] if "res://" in e or e.startswith(("SCRIPT ERROR", "SHADER ERROR", "USER ERROR"))]
    environment = [e for e in run["errors"] if e not in project]
    project_fatal = [e for e in project if not e.startswith(("WARNING", "USER WARNING"))]
    result = {"ok": not blank and not project_fatal, "path": str(out), "layout_path": str(layout), "blank": blank,
              "errors": project, "environment_errors": environment}
    if not result["ok"]:
        result["output_tail"] = run["output_tail"]
    return result


# --- .tscn parsing (text format) ---------------------------------------------------------

_SECTION_RE = re.compile(r"^\[(\w+)\s*(.*?)\]\s*$")
_ATTR_RE = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\w+\("[^"]*"\)|[^\s\]]+)')
_EXT_REF_RE = re.compile(r'ExtResource\("([^"]+)"\)')


def _parse_tscn(path: Path) -> list[dict]:
    ext: dict[str, str] = {}
    nodes: list[dict] = []
    current: dict | None = None
    for line in path.read_text(errors="replace").splitlines():
        m = _SECTION_RE.match(line)
        if m:
            kind, attrs = m.group(1), dict((k, v.strip('"')) for k, v in _ATTR_RE.findall(m.group(2)))
            current = None
            if kind == "ext_resource":
                ext[attrs.get("id", "")] = attrs.get("path", "")
            elif kind == "node":
                parent = attrs.get("parent")
                name = attrs.get("name", "")
                node_path = "." if parent is None else (name if parent == "." else f"{parent}/{name}")
                inst = _EXT_REF_RE.search(m.group(2)) if "instance=" in m.group(2) else None
                current = {"node_path": node_path, "name": name, "type": attrs.get("type"),
                           "script": None, "instance": ext.get(inst.group(1)) if inst else None}
                nodes.append(current)
            continue
        if current is not None and line.startswith("script = "):
            ref = _EXT_REF_RE.search(line)
            current["script"] = ext.get(ref.group(1)) if ref else line.split("=", 1)[1].strip()
    return nodes


@mcp.tool()
def find_scenes(query: str = "") -> list[dict]:
    """Find scenes/nodes. Empty query lists every .tscn with its root node. Otherwise returns nodes whose
    scene path, node path, type, script or instanced scene contains query (case-insensitive)."""
    q = query.lower()
    hits: list[dict] = []
    for scene in _iter_files(".tscn"):
        nodes = _parse_tscn(scene)
        res = _res(scene)
        if not q:
            root = nodes[0] if nodes else {}
            hits.append({"scene": res, "root_name": root.get("name"), "root_type": root.get("type"),
                         "script": root.get("script"), "node_count": len(nodes)})
            continue
        scene_match = q in res.lower()
        for n in nodes:
            fields = [n["node_path"], n["type"] or "", n["script"] or "", n["instance"] or ""]
            if scene_match or any(q in f.lower() for f in fields):
                hits.append({"scene": res, **n})
    return hits


@mcp.tool()
def scene_tree(scene: str) -> dict:
    """Full node tree of one scene (res:// path): node_path, name, type, script, instance for each node."""
    path = _to_path(scene)
    if path.suffix != ".tscn" or not path.exists():
        return {"error": f"Not a .tscn scene: {scene}"}
    return {"scene": scene, "nodes": _parse_tscn(path)}


if __name__ == "__main__":
    mcp.run()
