"""Fixtures for tools/mcp/godot_mcp.py. Godot never runs (skill: write-pytest).

GODOT_MCP_PATH loads another copy of the script, e.g. one taken with
`git show <sha>^:tools/mcp/godot_mcp.py`, to see a test red on the code before a fix.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Callable

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "godot_mcp.py"


@pytest.fixture
def mod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """A fresh godot_mcp module whose project root is tmp_path/project.

    Module constants are computed at import, so each one is patched, not just ROOT.
    GODOT points at a missing binary until a test sets it: nothing reaches a real Godot.
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
def fake_godot(mod: ModuleType, tmp_path: Path) -> Callable[..., None]:
    """Point GODOT at a shell script that prints stdout, then stderr, sleeps, and exits with code."""

    def make(stdout: str = "", stderr: str = "", code: int = 0, sleep: int = 0) -> None:
        bin_dir = tmp_path / "fake-godot"
        bin_dir.mkdir(exist_ok=True)
        (bin_dir / "stdout").write_text(stdout)
        (bin_dir / "stderr").write_text(stderr)
        script = bin_dir / "godot"
        script.write_text(
            "#!/bin/sh\n"
            f'cat "{bin_dir}/stdout"\n'
            f'cat "{bin_dir}/stderr" >&2\n'
            + (f"exec sleep {sleep}\n" if sleep else "")
            + f"exit {code}\n"
        )
        script.chmod(0o755)
        mod.GODOT = str(script)

    return make


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
