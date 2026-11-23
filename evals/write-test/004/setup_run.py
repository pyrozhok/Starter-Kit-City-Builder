"""Build one #22 run tree: python3 setup_run.py <arm: skill|base> <task a-h> <out_dir>.

Tree = $BASE (default 97ad620, the commit 004 ran on) minus evals/ and README.md (both arms), minus .claude/skills/write-test/
(baseline), minus the task's answer, as a single-commit repo (no history to read an answer from).
"""
import re
import shutil
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BASE = os.environ.get("BASE", "97ad620")
TEST = "tests/unit/test_builder.gd"

ANSWERS = {
    "a": ["test_structure_previous_from_first_wraps_to_last_and_switches_preview"],
    "b": ["test_rebuilding_same_structure_on_its_tile_does_not_charge"],
    "c": ["test_demolish_empties_tile"],
    "d": ["_hover_new_button", "test_build_is_ignored_while_pointer_is_over_ui",
          "test_demolish_is_ignored_while_pointer_is_over_ui"],
    "e": ["test_building_different_structure_over_tile_charges_new_price"],
    "f": ["test_rotate_turns_selector_quarter_turn_counterclockwise", "test_rotate_is_ignored_without_press"],
    "g": ["test_demolish_does_not_refund_cash"],
    "h": ["test_structure_next_from_last_structure_wraps_to_first",
          "test_structure_previous_from_first_wraps_to_last_and_switches_preview",
          # fail on the setup in today's tree (they await a frame / see _process), unlike at afc25eb
          "test_structure_next_switches_preview", "test_rotate_is_ignored_without_press"],
}


def drop_funcs(src: str, names: list[str]) -> str:
    for name in names:
        pat = re.compile(rf"^func {re.escape(name)}\(.*?(?=^func |\Z)", re.S | re.M)
        src, n = pat.subn("", src)
        assert n == 1, name
    return src


def sub1(src: str, old: str, new: str) -> str:
    assert src.count(old) == 1, old
    return src.replace(old, new)


def godot_import(tree: Path, tries: int = 2) -> None:
    """`godot --import` on a fresh tree, retried when Godot dies on a signal (#31: SIGABRT on a first import)."""
    cmd = [os.environ.get("GODOT_BIN", "godot"), "--headless", "--path", str(tree), "--import"]
    for _ in range(tries):
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode >= 0:
            break
    if r.returncode:
        raise subprocess.CalledProcessError(r.returncode, cmd, r.stdout, r.stderr)

def main(arm: str, task: str, out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    archive = subprocess.run(["git", "-C", str(REPO), "archive", BASE], check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", str(out)], input=archive, check=True)
    shutil.rmtree(out / "evals")
    (out / "README.md").unlink()
    if arm == "base":
        shutil.rmtree(out / ".claude/skills/write-test")

    test = out / TEST
    src = drop_funcs(test.read_text(), ANSWERS[task])
    if task == "d":
        src = sub1(src, "var viewport: SubViewport  # own viewport: GUT's panel can't be the hovered Control\n", "")
        src = sub1(src, "\tviewport = SubViewport.new()\n\tadd_child_autofree(viewport)\n\tviewport.add_child(builder)\n",
                   "\tadd_child_autofree(builder)\n")
        b = out / "scripts/builder.gd"
        bsrc = b.read_text()
        assert bsrc.count(" and not pointer_over_ui()") == 2
        b.write_text(bsrc.replace(" and not pointer_over_ui()", ""))
    if task == "h":
        src = sub1(src, "\tbuilder.set_process(false)  # after entering the tree (READY turns _process on); _process needs a camera, drive actions directly\n", "")
        src = sub1(src, "\tbuilder.add_child(builder.gridmap)\n",
                   "\tbuilder.set_process(false)  # _process needs a camera; drive actions directly\n\tbuilder.add_child(builder.gridmap)\n")
    test.write_text(src.rstrip("\n") + "\n")

    git = ["git", "-C", str(out)]
    subprocess.run([*git, "init", "-q", "-b", "main"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "-c", "user.name=eval", "-c", "user.email=eval@localhost", "commit", "-q", "-m", "base"], check=True)
    godot_import(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], Path(sys.argv[3]))
