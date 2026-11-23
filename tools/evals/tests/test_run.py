"""tools/evals/run.py and the import retry in evals/write-test/004/setup_run.py (#25, #31)."""
from __future__ import annotations

import json
import signal
import subprocess

import pytest


# --- godot --import retry (#31) ---

def test_import_retried_once_when_godot_aborts(setup_run, fake_godot, tmp_path):
    log = fake_godot(-signal.SIGABRT, 0)
    setup_run.godot_import(tmp_path)
    assert log.read_text().splitlines() == [f"--headless --path {tmp_path} --import"] * 2


def test_import_fails_when_godot_aborts_twice(setup_run, fake_godot, tmp_path):
    log = fake_godot(-signal.SIGABRT)
    with pytest.raises(subprocess.CalledProcessError) as e:
        setup_run.godot_import(tmp_path)
    assert e.value.returncode == -signal.SIGABRT
    assert len(log.read_text().splitlines()) == 2


def test_import_error_exit_is_not_retried(setup_run, fake_godot, tmp_path):
    log = fake_godot(1, 0)
    with pytest.raises(subprocess.CalledProcessError):
        setup_run.godot_import(tmp_path)
    assert len(log.read_text().splitlines()) == 1


def test_import_passes_first_time(setup_run, fake_godot, tmp_path):
    log = fake_godot(0)
    setup_run.godot_import(tmp_path)
    assert len(log.read_text().splitlines()) == 1


# --- stored results ---

def test_default_command_grades_stored_layouts(run, capsys):
    assert run.main([]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "| layout | frame | figcraft diff |",
        "|---|---|---|",
        "| evals/generate-ui/001/iter1_main_save.layout.json | MainMenu | 28/31 within ±2px |",
        "| evals/generate-ui/001/iter1_main_nosave_hover-NewGame.layout.json | MainMenu | 28/31 within ±2px |",
        "| evals/generate-ui/002/main_options.layout.json | Options | 3/58 within ±2px |",
        "| evals/generate-ui/002/main_options_drag_hover-BackButton.layout.json | Options_Hover | 3/58 within ±2px |",
    ]


# --- write-test ---

def test_run_names_task_major(run):
    assert run.run_names(["skill", "base"], ["a", "h"]) == ["skill-a", "base-a", "skill-h", "base-h"]


def test_write_test_row(run):
    g = {"run": "skill-b", "new_tests": ["test_x", "test_y"], "passed": 48, "failed": 0, "orphans": 0,
         "mutations": {"b1": ["test_x"], "b2": "SURVIVED", "b3": "NOT APPLIED: 'x' x0"}}
    stats = {"time": "34 s", "turns": 9, "cost": "$0.41", "error": False}
    assert run.write_test_row(g, stats) == ["skill-b", 2, "48/48", 0, "1/3", "b2, b3", "34 s", 9, "$0.41"]


def test_agent_stats(run, tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"duration_ms": 102400, "num_turns": 12, "total_cost_usd": 1.123, "is_error": False}))
    assert run.agent_stats(p) == {"time": "102 s", "turns": 12, "cost": "$1.12", "error": False}
    assert run.agent_stats(tmp_path / "none.json") == {"time": "-", "turns": "-", "cost": "-", "error": "no result"}


def test_grade_only_does_not_set_up_or_drive(run, tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(run.subprocess, "run", lambda *a, **k: calls.append(a))

    class Grade:
        @staticmethod
        def grade(n):
            return {"run": n, "new_tests": [], "passed": 1, "failed": 0, "orphans": 0, "mutations": {}}

    monkeypatch.setattr(run, "load", lambda path, name: Grade if name == "grade" else pytest.fail(name))
    run.main(["write-test", "-t", "a", "-a", "skill", "--grade-only", "--runs", str(tmp_path)])
    assert calls == []
    assert capsys.readouterr().out.splitlines()[-1] == "| skill-a | 0 | 1/1 | 0 | 0/0 | - | - | - | - |"


# --- review-pr ---

def test_review_cmd_is_headless_and_read_only(run):
    cmd = run.review_cmd(33)
    assert cmd[:3] == ["claude", "-p", "/review-pr 33"]
    tools = cmd[cmd.index("--allowedTools") + 1:cmd.index("--output-format")]
    assert tools == run.REVIEW_TOOLS
    assert not any(t in ("Edit", "Write") or "gh pr review" in t or "git push" in t for t in tools)
    assert "--permission-mode" not in cmd


# --- --model ---

def test_review_model_flag(run):
    cmd = run.review_cmd(33, "claude-sonnet-5")
    assert cmd[cmd.index("--model") + 1] == "claude-sonnet-5"
    assert run.review_cmd(33)[run.review_cmd(33).index("--model") + 1] == "claude-opus-5-5"


def test_write_test_passes_model_to_drive(run, tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(run.subprocess, "run", lambda *a, **k: calls.append(k["env"]["MODEL"]))

    class Mod:
        main = staticmethod(lambda *a: None)
        grade = staticmethod(lambda n: {"run": n, "new_tests": [], "passed": 1, "failed": 0, "orphans": 0, "mutations": {}})

    monkeypatch.setattr(run, "load", lambda path, name: Mod)
    run.main(["write-test", "-t", "a", "-a", "skill", "--runs", str(tmp_path), "--model", "claude-sonnet-5"])
    run.main(["write-test", "-t", "a", "-a", "skill", "--runs", str(tmp_path)])
    assert calls == ["claude-sonnet-5", "claude-opus-5-5"]


def test_drive_sh_reads_model(run, tmp_path):
    """drive.sh hands $MODEL to claude: a fake claude on PATH records its argv."""
    import os
    bin_ = tmp_path / "bin"; bin_.mkdir()
    (bin_ / "claude").write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$RUNS/argv"\necho {}\n')
    (bin_ / "claude").chmod(0o755)
    (tmp_path / "skill-a").mkdir()
    subprocess.run(["git", "init", "-q", str(tmp_path / "skill-a")], check=True)
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "RUNS": str(tmp_path), "MODEL": "claude-sonnet-5"}
    subprocess.run(["bash", str(run.WT004 / "drive.sh"), "skill-a"], env=env, check=True, capture_output=True)
    argv = (tmp_path / "argv").read_text().splitlines()
    assert argv[argv.index("--model") + 1] == "claude-sonnet-5"
