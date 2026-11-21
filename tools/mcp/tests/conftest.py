"""Fixtures for tools/mcp/godot_mcp.py. Godot never runs (skill: write-pytest).

GODOT_MCP_PATH loads another copy of the script, e.g. one taken with
`git show <sha>^:tools/mcp/godot_mcp.py`, to see a test red on the code before a fix.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "godot_mcp.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# The fake binary. It does only what godot_mcp relies on Godot doing: find the project through
# --path, write JUnit where -gjunit_xml_file points, print, change files, exit. A command line
# godot_mcp gets wrong therefore loses its results here as it would with the real Godot.
_FAKE_GODOT = """
import json, sys, time
from pathlib import Path

here = Path(__file__).parent
args = sys.argv[1:]
with open(here / "calls.jsonl", "a") as f:
    f.write(json.dumps(args) + "\\n")
if "--path" not in args:
    sys.stderr.write("ERROR: no project: --path missing\\n")
    sys.exit(2)
project = Path(args[args.index("--path") + 1])
rules = json.loads((here / "rules.json").read_text())
rule = next((r for r in rules if r["when"] is None or r["when"] in args), None)
if rule is None:
    sys.stderr.write("ERROR: fake Godot has no rule for " + " ".join(args) + "\\n")
    sys.exit(2)
for rel, text in rule["write"].items():
    (project / rel).write_text(text)
for rel in rule["delete"]:
    (project / rel).unlink()
junit = next((a.split("=", 1)[1] for a in args if a.startswith("-gjunit_xml_file=res://")), None)
if rule["junit"] is not None and junit:
    out = project / junit.removeprefix("res://")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rule["junit"])
sys.stdout.write(rule["stdout"])
sys.stdout.flush()
sys.stderr.write(rule["stderr"])
sys.stderr.flush()
time.sleep(rule["sleep"])
sys.exit(rule["code"])
"""


class FakeGodot:
    """An executable stand-in for Godot. `on(when, ...)` adds a rule: the first rule whose `when`
    is one of the arguments (or is None) decides what a call prints, writes and returns."""

    def __init__(self, directory: Path) -> None:
        directory.mkdir()
        self.dir = directory
        self.path = directory / "godot"
        self.path.write_text(f"#!{sys.executable} -I\n{_FAKE_GODOT}")
        self.path.chmod(0o755)
        self._rules: list[dict] = []
        self._save()

    @staticmethod
    def fixture(name: str) -> str:
        return (FIXTURES / name).read_text()

    def on(self, when: str | None = None, *, capture: str | None = None, stdout: str = "",
           stderr: str = "", code: int = 0, sleep: float = 0, junit: str | None = None,
           write: dict[str, str] | None = None, delete: tuple[str, ...] = ()) -> FakeGodot:
        """capture: replay fixtures/gut-9.7.1-<capture>.* (stdout, stderr, junit); `code` stays explicit."""
        if capture:
            stdout = self.fixture(f"gut-9.7.1-{capture}.stdout.txt")
            stderr = self.fixture(f"gut-9.7.1-{capture}.stderr.txt")
            junit = self.fixture(f"gut-9.7.1-{capture}.junit.xml")
        self._rules.append({"when": when, "stdout": stdout, "stderr": stderr, "code": code,
                            "sleep": sleep, "junit": junit, "write": write or {}, "delete": list(delete)})
        self._save()
        return self

    @property
    def calls(self) -> list[list[str]]:
        """Arguments of each call, in order (the binary path itself left out)."""
        log = self.dir / "calls.jsonl"
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def _save(self) -> None:
        (self.dir / "rules.json").write_text(json.dumps(self._rules))


@pytest.fixture
def mod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """A fresh godot_mcp module whose project root is tmp_path/project.

    Module constants are computed at import, so each one is patched, not just ROOT.
    GODOT points at a missing binary until a test asks for `godot`: nothing reaches a real Godot.
    """
    path = Path(os.environ.get("GODOT_MCP_PATH") or SCRIPT)
    spec = importlib.util.spec_from_file_location("godot_mcp_under_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    root = tmp_path / "project"
    root.mkdir()
    monkeypatch.setattr(module, "ROOT", root)
    monkeypatch.setattr(module, "RESULTS_XML", root / ".godot" / "gut_results.xml")
    monkeypatch.setattr(module, "SCREENSHOTS", root / ".godot" / "screenshots", raising=False)
    monkeypatch.setattr(module, "GODOT", str(tmp_path / "no-godot"))
    # git in the code under test and in the fixtures sees no user config and stops at tmp_path.
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    return module


@pytest.fixture
def godot(mod: ModuleType, tmp_path: Path) -> FakeGodot:
    """GODOT pointed at a FakeGodot with no rules yet."""
    fake = FakeGodot(tmp_path / "fake-godot")
    mod.GODOT = str(fake.path)
    return fake


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=root,
                   check=True, capture_output=True)


@pytest.fixture
def repo(mod: ModuleType) -> Path:
    """ROOT as a git repo with one commit: tracked.txt, dirty.txt, .gitignore (ignores ignored.txt)."""
    if not shutil.which("git"):
        pytest.skip("git not installed")
    root: Path = mod.ROOT
    (root / "tracked.txt").write_text("a\n")
    (root / "dirty.txt").write_text("a\n")
    (root / ".gitignore").write_text("ignored.txt\n")
    _git(root, "init", "-q")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")
    return root
