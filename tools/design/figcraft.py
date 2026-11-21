# /// script
# requires-python = ">=3.10"
# ///
"""Read a figcraft mockup (.figcraft = zip with document.json) without the figcraft MCP.

  uv run --script tools/design/figcraft.py tree design/main_menu.figcraft [FRAME]
      Layer table of FRAME (name or id; default: list top-level frames): id, path, type,
      x/y/w/h relative to the frame, fill, stroke, radius, auto-layout, font, text.
  uv run --script tools/design/figcraft.py diff design/main_menu.figcraft FRAME LAYOUT.json MAP.json [--tol 2]
      Geometry of each mapped layer vs the node rect from godot.screenshot's .layout.json.
      MAP.json: {"<layer id or path>": "<node path from the scene root>", ...}.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile


def load(path: str) -> dict:
    with zipfile.ZipFile(path) as z:
        return json.loads(z.read("document.json"))


def hex_color(c: dict, opacity: float = 1.0) -> str:
    rgb = "".join(f"{round(c[k] * 255):02x}" for k in "rgb")
    a = c.get("a", 1.0) * opacity
    return f"#{rgb}" + ("" if a >= 0.999 else f"/{a:.2f}")


def paint(p: dict) -> str:
    if p.get("type") == "solid":
        return hex_color(p["color"], p.get("opacity", 1.0))
    if p.get("type") == "gradient":
        stops = " → ".join(f"{hex_color(s['color'])}@{s['position']:g}" for s in p["stops"])
        return f"{p.get('kind', '')}-gradient {stops} from {p.get('from')} to {p.get('to')}"
    return p.get("type", "?")


def describe(n: dict) -> dict:
    out: dict = {}
    fills = [paint(f) for f in n.get("fills") or [] if f.get("visible", True)]
    if fills:
        out["fill"] = ", ".join(fills)
    if n.get("strokes"):
        s = n.get("stroke", {})
        out["stroke"] = f"{', '.join(paint(p) for p in n['strokes'])} w{s.get('weight')}" + (
            f" sides(t,r,b,l)={s['sides']}" if s.get("sides") else "")
    if n.get("corners"):
        radii = n["corners"]["radii"]
        out["radius"] = radii[0] if len(set(radii)) == 1 else radii
    if n.get("opacity", 1.0) < 1.0:
        out["opacity"] = n["opacity"]
    if n.get("visible") is False:
        out["visible"] = False
    if n.get("layout") and n["layout"].get("mode") not in (None, "none"):
        lay = n["layout"]
        out["layout"] = (f"{lay['mode']} gap {lay.get('gap', 0):g} pad(t,r,b,l) {lay.get('padding')} "
                         f"align {lay.get('main_align')}/{lay.get('cross_align')}")
    if n.get("child_layout"):
        cl = n["child_layout"]
        out["sizing"] = f"{cl.get('sizing_h')}/{cl.get('sizing_v')}"
    if n.get("constraints"):
        out["constraints"] = f"{n['constraints'].get('horizontal')}/{n['constraints'].get('vertical')}"
    if n.get("style"):
        st = n["style"]
        ls = st.get("letter_spacing", {})
        out["font"] = (f"{st.get('font_family')} {st.get('font_style', '')} {st.get('font_size'):g}px"
                       + (f" ls {ls.get('value'):g}%" if ls.get("value") else "")
                       + (f" case {st['case']}" if st.get("case") not in (None, "original") else "")
                       + (f" align {n['align_h']}" if n.get("align_h") else ""))
    if n.get("characters") is not None:
        out["text"] = n["characters"]
    for e in n.get("effects") or []:
        if e.get("visible", True):
            extra = f" offset {e['offset']} {hex_color(e['color'])}" if "offset" in e else ""
            out.setdefault("effects", []).append(f"{e['type']} r{e.get('radius', 0):g}{extra}")
    if n.get("component") is not None:
        out["component"] = n["component"]
    if n.get("props") and n["type"] == "instance":
        out["props"] = n["props"]
    return out


def walk(doc: dict, frame_id: int):
    """Yield (node, path, x, y) for every layer under the frame; x/y relative to the frame."""
    nodes = doc["nodes"]

    def rec(nid: int, path: str, ox: float, oy: float):
        n = nodes[str(nid)]
        t = n.get("transform") or [1, 0, 0, 1, 0, 0]
        x, y = ox + t[4], oy + t[5]
        yield n, path, x, y
        for c in n.get("children", []):
            child = nodes[str(c)]
            if child["type"] == "vector":  # icon glyph geometry, not a layout layer
                continue
            yield from rec(c, f"{path}/{child['name']}", x, y)

    frame = nodes[str(frame_id)]
    for c in frame.get("children", []):
        yield from rec(c, nodes[str(c)]["name"], 0.0, 0.0)


def find_frame(doc: dict, key: str) -> int:
    for nid, n in doc["nodes"].items():
        if n["type"] in ("frame", "component", "componentSet") and (key == nid or key == n["name"]):
            return int(nid)
    sys.exit(f"frame not found: {key}")


def top_frames(doc: dict) -> list[dict]:
    return [doc["nodes"][str(c)] for p in doc["pages"] for c in doc["nodes"][str(p)].get("children", [])]


def cmd_tree(args) -> None:
    doc = load(args.file)
    if not args.frame:
        for f in top_frames(doc):
            print(f"{f['id']}\t{f['name']}\t{f['type']}\t{f['width']:g}×{f['height']:g}")
        return
    fid = find_frame(doc, args.frame)
    f = doc["nodes"][str(fid)]
    print(f"# {f['name']} (id {fid}) {f['width']:g}×{f['height']:g} {describe(f)}")
    for n, path, x, y in walk(doc, fid):
        depth = path.count("/")
        info = "  ".join(f"{k}={v}" for k, v in describe(n).items())
        print(f"{'  ' * depth}{n['id']} {n['name']} [{n['type']}] "
              f"@({x:g},{y:g}) {n.get('width', 0):g}×{n.get('height', 0):g}  {info}")


def cmd_diff(args) -> None:
    doc = load(args.file)
    fid = find_frame(doc, args.frame)
    layers = {}
    for n, path, x, y in walk(doc, fid):
        rect = (x, y, n.get("width", 0.0), n.get("height", 0.0))
        layers[str(n["id"])] = (path, rect)
        layers[path] = (path, rect)
    with open(args.layout) as fh:
        layout = json.load(fh)
    controls = {c["path"]: c for c in layout["controls"]}
    with open(args.map) as fh:
        mapping = json.load(fh)

    print("| layer | node | mockup x,y w×h | fact x,y w×h | Δx | Δy | Δw | Δh | ok |")
    print("|---|---|---|---|---|---|---|---|---|")
    bad = 0
    for layer_key, node_path in mapping.items():
        if layer_key not in layers:
            print(f"| {layer_key} | {node_path} | layer not found | | | | | | ✗ |")
            bad += 1
            continue
        lpath, (x, y, w, h) = layers[layer_key]
        c = controls.get(node_path)
        if c is None:
            print(f"| {lpath} | {node_path} | {x:g},{y:g} {w:g}×{h:g} | node not visible/found | | | | | ✗ |")
            bad += 1
            continue
        d = [c["x"] - x, c["y"] - y, c["w"] - w, c["h"] - h]
        ok = all(abs(v) <= args.tol for v in d)
        bad += not ok
        print(f"| {lpath} | {node_path} | {x:g},{y:g} {w:g}×{h:g} | {c['x']:g},{c['y']:g} {c['w']:g}×{c['h']:g} | "
              + " | ".join(f"{v:+.0f}" for v in d) + f" | {'✓' if ok else '✗'} |")
    print(f"\n{len(mapping) - bad}/{len(mapping)} within ±{args.tol:g}px")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tree")
    t.add_argument("file")
    t.add_argument("frame", nargs="?")
    t.set_defaults(func=cmd_tree)
    d = sub.add_parser("diff")
    d.add_argument("file")
    d.add_argument("frame")
    d.add_argument("layout")
    d.add_argument("map")
    d.add_argument("--tol", type=float, default=2.0)
    d.set_defaults(func=cmd_diff)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
