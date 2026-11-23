# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=2.3,<3"]
# ///
"""Rerun the evals and print scores, so a skill edit comes with before/after numbers (#25).

  uv run --script tools/evals/run.py                      # grade stored results (generate-ui layout diffs)
  uv run --script tools/evals/run.py write-test [-t a,h] [-a skill,base] [--grade-only] [--runs DIR]
  uv run --script tools/evals/run.py review-pr 33 [--commit SHA] [--out DIR]

write-test reuses evals/write-test/004 (setup_run.py, drive.sh, grade.py): one fresh headless
`claude -p` per arm and task, then each grading mutation against the agent's tests.
review-pr runs `claude -p "/review-pr N"` in a detached worktree at the PR head with this
checkout's review-pr skill (the change under test) and 006's allow-list; nothing is posted.
Its grading is by reading the review against the run's answer key.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WT004 = REPO / "evals/write-test/004"
FIGCRAFT = REPO / "tools/design/figcraft.py"
MODEL = "claude-opus-5-5"

# generate-ui: (mockup, frame, stored layout, map) per graded state
LAYOUTS = [
    ("design/main_menu.figcraft", "MainMenu", "evals/generate-ui/001/iter1_main_save.layout.json", "design/main_menu.map.json"),
    ("design/main_menu.figcraft", "MainMenu", "evals/generate-ui/001/iter1_main_nosave_hover-NewGame.layout.json", "design/main_menu.map.json"),
    ("design/options.figcraft", "Options", "evals/generate-ui/002/main_options.layout.json", "design/options.map.json"),
    ("design/options.figcraft", "Options_Hover", "evals/generate-ui/002/main_options_drag_hover-BackButton.layout.json", "design/options.map.json"),
]

# 006's allow-list: read-only gh/git/grep, the godot gates, read tools. No writes, no `gh pr review`.
REVIEW_TOOLS = ["Bash(gh pr view:*)", "Bash(gh pr diff:*)", "Bash(git log:*)", "Bash(git show:*)",
                "Bash(git diff:*)", "Bash(git status:*)", "Bash(grep:*)", "mcp__godot__build",
                "mcp__godot__run_tests", "Read", "Grep", "Glob", "Skill", "Agent"]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def table(header: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def run_names(arms: list[str], tasks: list[str]) -> list[str]:
    return [f"{a}-{t}" for t in tasks for a in arms]


def agent_stats(path: Path) -> dict:
    """duration, turns, cost and error flag from a `claude -p --output-format json` result."""
    try:
        d = json.loads(path.read_text())
    except (OSError, ValueError):
        return {"time": "-", "turns": "-", "cost": "-", "error": "no result"}
    return {"time": f"{d.get('duration_ms', 0) / 1000:.0f} s", "turns": d.get("num_turns", "-"),
            "cost": f"${d['total_cost_usd']:.2f}" if "total_cost_usd" in d else "-",
            "error": d.get("is_error", False)}


def write_test_row(g: dict, stats: dict) -> list:
    muts = g["mutations"]
    caught = [m for m, v in muts.items() if isinstance(v, list)]
    missed = sorted(set(muts) - set(caught))
    return [g["run"], len(g["new_tests"]), f"{g['passed']}/{g['passed'] + g['failed']}" if g.get("passed") is not None else "-",
            g.get("orphans", "-"), f"{len(caught)}/{len(muts)}", ", ".join(missed) or "-",
            stats["time"], stats["turns"], stats["cost"]]


def cmd_grade(_args) -> int:
    rows = []
    for fig, frame, layout, mapping in LAYOUTS:
        r = subprocess.run([sys.executable, str(FIGCRAFT), "diff", fig, frame, layout, mapping],
                           cwd=REPO, capture_output=True, text=True, check=True)
        rows.append([layout, frame, r.stdout.strip().splitlines()[-1]])
    print(table(["layout", "frame", "figcraft diff"], rows))
    return 0


def cmd_write_test(args) -> int:
    runs = Path(args.runs)
    names = run_names(args.arms.split(","), args.tasks.split(","))
    os.environ["RUNS"] = str(runs)
    if not args.grade_only:
        setup = load(WT004 / "setup_run.py", "setup_run")
        for n in names:
            arm, task = n.split("-")
            setup.main(arm, task, runs / n)
        subprocess.run(["bash", str(WT004 / "drive.sh"), *names], check=True, env={**os.environ, "RUNS": str(runs)})
    grade = load(WT004 / "grade.py", "grade")
    rows = []
    for n in names:
        g = grade.grade(n)
        print(json.dumps(g), file=sys.stderr, flush=True)
        rows.append(write_test_row(g, agent_stats(runs / f"{n}.json")))
    print(table(["run", "new tests", "suite", "orphans", "mutations caught", "survived", "time", "turns", "cost"], rows))
    return 0


def review_cmd(pr: int) -> list[str]:
    return ["claude", "-p", f"/review-pr {pr}", "--model", MODEL, "--mcp-config", ".mcp.json",
            "--allowedTools", *REVIEW_TOOLS, "--output-format", "json"]


def cmd_review_pr(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sha = args.commit or subprocess.run(
        ["gh", "pr", "view", str(args.pr), "--repo", "pyrozhok/Starter-Kit-City-Builder", "--json", "headRefOid", "-q", ".headRefOid"],
        capture_output=True, text=True, check=True).stdout.strip()
    wt = out / f"wt-{args.pr}"
    if wt.exists():
        subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", str(wt)], check=True)
    subprocess.run(["git", "-C", str(REPO), "fetch", "-q", "fork", sha], check=False)
    subprocess.run(["git", "-C", str(REPO), "worktree", "add", "-q", "--detach", str(wt), sha], check=True)
    skill = wt / ".claude/skills/review-pr"
    shutil.rmtree(skill, ignore_errors=True)
    shutil.copytree(REPO / ".claude/skills/review-pr", skill)
    load(WT004 / "setup_run.py", "setup_run").godot_import(wt)
    res = out / f"review-{args.pr}.json"
    with res.open("w") as fh:
        subprocess.run(review_cmd(args.pr), cwd=wt, stdout=fh, check=False)
    s = agent_stats(res)
    try:
        (out / f"review-{args.pr}.md").write_text(json.loads(res.read_text()).get("result", ""))
    except ValueError:
        pass
    print(table(["PR", "commit", "time", "turns", "cost", "error", "review"],
                [[args.pr, sha[:7], s["time"], s["turns"], s["cost"], s["error"], out / f"review-{args.pr}.md"]]))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    w = sub.add_parser("write-test", help="setup, agent runs and mutation grading (evals/write-test/004)")
    w.add_argument("-t", "--tasks", default="a,b,c,d,e,f,g,h")
    w.add_argument("-a", "--arms", default="skill,base")
    w.add_argument("--runs", default=os.environ.get("RUNS", "/tmp/write-test-004"))
    w.add_argument("--grade-only", action="store_true", help="grade existing runs, no setup or agent")
    w.set_defaults(func=cmd_write_test)
    r = sub.add_parser("review-pr", help="headless /review-pr on one PR in a fresh worktree")
    r.add_argument("pr", type=int)
    r.add_argument("--commit", help="PR head to review (default: gh pr view headRefOid)")
    r.add_argument("--out", default="/tmp/review-pr-eval")
    r.set_defaults(func=cmd_review_pr)
    args = ap.parse_args(argv)
    return getattr(args, "func", cmd_grade)(args)


if __name__ == "__main__":
    sys.exit(main())
