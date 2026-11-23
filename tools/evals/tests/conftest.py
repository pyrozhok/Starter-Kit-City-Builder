"""Fixtures for tools/evals/run.py. Neither Godot nor claude runs (skill: write-pytest).

RUN_PATH / SETUP_RUN_PATH load other copies, e.g. from `git show <sha>^:...`, to see a test red.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


def _load(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def run():
    return _load(os.environ.get("RUN_PATH", REPO / "tools/evals/run.py"), "run_under_test")


@pytest.fixture
def setup_run():
    return _load(os.environ.get("SETUP_RUN_PATH", REPO / "evals/write-test/004/setup_run.py"), "setup_under_test")


@pytest.fixture
def fake_godot(tmp_path, monkeypatch):
    """Godot as a process: records each argv; `rules` is the exit per call (negative = die on that signal)."""
    log = tmp_path / "calls"

    def make(*rules: int) -> Path:
        exe = tmp_path / "godot"
        exe.write_text(f"""#!/usr/bin/env python3
import os, signal, sys
log = {str(log)!r}
n = sum(1 for _ in open(log)) if os.path.exists(log) else 0
open(log, "a").write(" ".join(sys.argv[1:]) + "\\n")
rules = {list(rules)!r}
code = rules[min(n, len(rules) - 1)]
if code < 0:
    os.kill(os.getpid(), -code)
sys.exit(code)
""")
        exe.chmod(0o755)
        monkeypatch.setenv("GODOT_BIN", str(exe))
        return log

    return make
