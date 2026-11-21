"""Mutation check for tools/mcp/tests: each mutation breaks one behavior of godot_mcp.py in a copy,
loaded through GODOT_MCP_PATH; at least one test must go red. Mutations match godot_mcp.py at 4dfc4a6.

  python3 -I evals/write-pytest/001/mutate.py <repo> <scratch dir>
"""
import os, re, subprocess, sys
from pathlib import Path
repo = Path(sys.argv[1]); out = Path(sys.argv[2])
src = (repo / "tools/mcp/godot_mcp.py").read_text()
M = [
 ("ansi", 'output = _ANSI_RE.sub("", proc.stdout + proc.stderr)', 'output = proc.stdout + proc.stderr'),
 ("at-append", 'errors[-1] += f" [{at.group(1)}]"', 'pass'),
 ("dedupe", 'return list(dict.fromkeys(errors))', 'return errors'),
 ("ok-error-tuple", 'e.startswith(("SCRIPT ERROR", "ERROR", "USER ERROR")) for e in errors),', 'e.startswith(("SCRIPT ERROR", "USER ERROR")) for e in errors),'),
 ("exit-code-ok", '"ok": proc.returncode == 0 and', '"ok":'),
 ("orphan-case", 'r"^(\\d+) orphans$", re.MULTILINE', 'r"^\\W*(\\d+) orphans$", re.MULTILINE | re.IGNORECASE'),
 ("failure-fallback", 'failure.text or failure.get("message") or ""', 'failure.text or ""'),
 ("pending", 'elif case.find("skipped") is not None:', 'elif False:'),
 ("stale-xml", '    RESULTS_XML.unlink(missing_ok=True)\n', ''),
 ("truncated", 'except ET.ParseError:  # truncated file, e.g. Godot killed mid-write\n        cases = None', 'except ET.ParseError:\n        cases = []'),
 ("no-tests-ran", 'if not ran:', 'if False:'),
 ("orphans-ok", ' and not run["orphans"]', ''),
 ("script-errors-ok", ' and not script_errors\n', '\n'),
 ("plain-error", 'script_errors = [e for e in run["errors"] if e.startswith(("SCRIPT ERROR", "USER ERROR"))]', 'script_errors = [e for e in run["errors"] if e.startswith(("SCRIPT ERROR", "ERROR", "USER ERROR"))]'),
 ("gselect", 'args += [f"-gdir={_res(p.parent)}", f"-gselect={p.name}"]', 'args += [f"-gtest={_res(p)}"]'),
 ("test-name", 'args.append(f"-gunit_test_name={test_name}")', 'pass'),
 ("tail-pop", 'step.pop("output_tail", None)', 'pass'),
 ("to-path", '        raise ValueError(f"Path escapes project: {res_path}")', '        pass'),
 ("skip-dirs", 'SKIP_DIRS = {".godot", "addons", ".git"}', 'SKIP_DIRS = {".git"}'),
 ("case", 'q = query.lower()', 'q = query'),
 ("instance", 'inst = _EXT_REF_RE.search(m.group(2)) if "instance=" in m.group(2) else None', 'inst = None'),
 ("script-ref", 'current["script"] = ext.get(ref.group(1)) if ref else', 'current["script"] = None if ref else'),
 ("nested-path", 'node_path = "." if parent is None else (name if parent == "." else f"{parent}/{name}")', 'node_path = "." if parent is None else name'),
 ("scene-match", 'scene_match = q in res.lower()', 'scene_match = False'),
 ("tree-suffix", 'if path.suffix != ".tscn" or not path.exists():', 'if not path.exists():'),
 ("tool-param", 'def scene_tree(scene: str) -> dict:', 'def scene_tree(scene: str, depth: int = 0) -> dict:'),
]
env = {**os.environ, "GODOT_BIN": "/nonexistent"}
survivors = []
for name, old, new in M:
    assert src.count(old) == 1, (name, src.count(old))
    p = out / f"mut-{name}.py"; p.write_text(src.replace(old, new))
    r = subprocess.run(["uv", "run", "-q", "--with", "pytest", "--with", "mcp>=2.3,<3", "pytest",
                        "--import-mode=importlib", "-p", "no:cacheprovider", "-q", "-rf", "tools"],
                       cwd=repo, env={**env, "GODOT_MCP_PATH": str(p)}, capture_output=True, text=True)
    failed = sorted({l.split("::", 1)[1].split(" ")[0] for l in r.stdout.splitlines() if l.startswith("FAILED")})
    print(f"{name:18} {len(failed)} red: {', '.join(failed)}")
    if not failed: survivors.append(name)
print("SURVIVED:", survivors)
