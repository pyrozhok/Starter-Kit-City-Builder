"""Prompts copied verbatim from evals/write-test/tasks.md (a-d) and tasks-003.md (e-h)."""
TAIL = " Use the project skill `write-test`. Don't commit; leave your changes in the working tree and report what you did."
P = {
 "a": "`structure_previous` in `scripts/builder.gd` isn't covered by any test. Add a GUT test for it.",
 "b": "Building the same structure again on a tile that already holds it must not charge cash. Cover this with a GUT test.",
 "c": "Demolish must return the tile to -1 (empty). Cover it with a GUT test.",
 "d": "Bug: clicking on the UI also builds or demolishes on the map under the pointer (e.g. clicking a menu button places a road behind it). Write a test that catches it, then fix it.",
 "e": "Building a different structure over a tile that already holds one must charge the new structure's price. Cover it with a GUT test.",
 "f": "`rotate` in `scripts/builder.gd` isn't covered by any test. Add a GUT test for it.",
 "g": "Demolish must not refund any cash. Cover it with a GUT test.",
 "h": "`structure_next` from the last structure isn't covered by any test. Add a GUT test for it.",
}
def prompt(arm, t):
    tail = TAIL if arm == "skill" else TAIL.replace(" Use the project skill `write-test`.", "")
    return P[t] + tail
if __name__ == "__main__":
    import sys; print(prompt(sys.argv[1], sys.argv[2]))
