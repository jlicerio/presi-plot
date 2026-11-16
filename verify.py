#!/usr/bin/env python3
"""Hard pass on the Presi sheet: every symbol, address and dimension."""

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import ezdxf

HERE = Path("/Users/selfsim/projects/presi-plot-site")
SRC = Path("/Users/selfsim/projects/wmx1-convert-stage-sim")

problems = []
notes = []


def check(ok, label, detail=""):
    notes.append((bool(ok), label, detail))
    if not ok:
        problems.append(label + (f" — {detail}" if detail else ""))


# ---------------------------------------------------------------- source data
with open(SRC / "patch.csv", newline="") as fh:
    csv_rows = list(csv.DictReader(fh))

show = json.loads((HERE / "show.json").read_text()) if (HERE / "show.json").exists() else None
fixtures_js = (SRC / "fixtures.js").read_text()
raw = fixtures_js.replace("export const SHOW", "SHOW").replace("export ", "")

data = json.loads((HERE / "data-dump.json").read_text())

check(len(csv_rows) == 41, "patch.csv holds 41 fixtures", str(len(csv_rows)))
check(len(data) == 41, "sheet holds 41 fixtures", str(len(data)))

# addresses from the csv, keyed by the desk fixture name tail
def short(fixture):
    tail = fixture.split(".")[-1]
    head = fixture.split(".")[0].lower()
    if "moving head" in head:
        return f"MH-{tail}"
    if "rgbw" in head:
        return f"PAR-{tail}"
    if "stage panel" in head:
        return f"SP-{tail}"
    if "beam" in head:
        return f"DW-{tail}"
    if "aura" in head:
        return f"AURA-{tail}"
    return f"LASER-{tail}"


csv_map = {}
for r in csv_rows:
    csv_map[short(r["fixture"])] = {
        "address": int(r["address"]),
        "end": int(r["end"]),
        "channels": int(r["channels"]),
        "group": r["wmx1_group"],
    }

sheet_map = {r["name"]: r for r in data}

check(set(csv_map) == set(sheet_map), "fixture names match the source",
      f"only csv: {sorted(set(csv_map) - set(sheet_map))}, only sheet: {sorted(set(sheet_map) - set(csv_map))}")

addr_bad = []
for name, row in sheet_map.items():
    src = csv_map.get(name)
    if not src:
        continue
    if row["address"] != src["address"] or row["channels"] != src["channels"]:
        addr_bad.append(f"{name}: sheet {row['address']}/{row['channels']} vs csv {src['address']}/{src['channels']}")
check(not addr_bad, "address and channel count match the source", "; ".join(addr_bad[:5]))

# coverage: 1..512, no overlaps
pairs = sorted((r["address"], r["address"] + r["channels"] - 1, r["name"]) for r in data)
overlaps = [(a, b) for a, b in zip(pairs, pairs[1:]) if b[0] <= a[1]]
check(not overlaps, "no address overlaps", str(overlaps[:3]))
used = set()
for a, b, _ in pairs:
    used.update(range(a, b + 1))
check(used == set(range(1, 513)), "channels 1–512 all allocated",
      f"missing {sorted(set(range(1, 513)) - used)[:5]}")
check(sum(r["channels"] for r in data) == 512, "channel total is 512",
      str(sum(r["channels"] for r in data)))

# ---------------------------------------------------------------- the drawing
doc = ezdxf.readfile(HERE / "presi-plot.dxf")
msp = doc.modelspace()
texts = [(e.dxf.text, e.dxf.insert.x, e.dxf.insert.y, e.dxf.height, e.dxf.layer) for e in msp.query("TEXT")]
lines = [e for e in msp.query("LINE")]
circles = list(msp.query("CIRCLE"))
audit = doc.audit()
check(len(audit.errors) == 0, "DXF audit clean", f"{len(audit.errors)} errors")

# every fixture label present
labels = {t[0] for t in texts}
missing_labels = [n for n in sheet_map if n not in labels]
check(not missing_labels, "every fixture has an ID label", str(missing_labels[:5]))

# every address range present
missing_ranges = []
for name, r in sheet_map.items():
    want = f"{r['address']}-{r['address'] + r['channels'] - 1}"
    if want not in {t[0] for t in texts}:
        missing_ranges.append(f"{name} {want}")
check(not missing_ranges, "every fixture has its address range on the plan", str(missing_ranges[:5]))

# label sits next to its symbol
by_layer_group = defaultdict(list)
for name, r in sheet_map.items():
    by_layer_group[r["group"]].append((name, r))

label_pos = {t[0]: (t[1], t[2]) for t in texts}
far = []
for name, r in sheet_map.items():
    if name not in label_pos:
        continue
    lx, ly = label_pos[name]
    # symbol is at the same y-origin, within the leader reach
    if not (40 < lx < 270 and 60 < ly < 265):
        far.append(f"{name}@{lx:.0f},{ly:.0f}")
check(not far, "labels stay inside the plan area", str(far[:5]))

# symbol shapes per group
def count_in_layer(layer):
    c = sum(1 for e in circles if e.dxf.layer == layer)
    r = sum(1 for e in msp.query("LINE") if e.dxf.layer == layer)
    return c, r

expect = {
    "Moving Heads": (16, "circle+cross"),
    "RGBW Pars": (8, "square"),
    "Stage Panels": (10, "square+diagonal"),
    "DJ World Beams": (4, "rectangle"),
    "Aura": (2, "double circle"),
    "Laser": (1, "double circle"),
}
layer_of = {
    "Moving Heads": "FIX-MOVING", "RGBW Pars": "FIX-RGBW", "Stage Panels": "FIX-STAGE",
    "DJ World Beams": "FIX-DJ", "Aura": "FIX-AURA", "Laser": "FIX-LASER",
}
for group, (qty, shape) in expect.items():
    layer = layer_of[group]
    members = [r for r in data if r["group"] == group]
    check(len(members) == qty, f"{group}: {qty} fixtures in data", str(len(members)))
    if "circle" in shape:
        sym = qty * (2 if "double" in shape else 1)
    else:
        sym = qty
    c = sum(1 for e in circles if e.dxf.layer == layer and e.dxf.center.y > 60)
    l = sum(1 for e in lines if e.dxf.layer == layer
            and e.dxf.start.y > 60 and e.dxf.end.y > 60)
    if "circle" in shape:
        check(c == sym, f"{group}: {qty} symbols drawn as {shape}", f"{c} circles on {layer}")
    else:
        # each square = 4 lines, diagonal adds 1
        want_lines = qty * (5 if "diagonal" in shape else 4) + qty * 2  # shape + two leader segments
        check(l >= want_lines, f"{group}: {qty} symbols drawn as {shape}", f"{l} lines on {layer}, want {want_lines}")

# legend rows
legend_names = ["Moving Heads", "RGBW Pars", "Stage Panels", "DJ World Beams", "Aura", "Laser"]
for g in legend_names:
    check(g in labels, f"legend lists {g}")
    members = [r for r in data if r["group"] == g]
    lo = min(r["address"] for r in members)
    hi = max(r["address"] + r["channels"] - 1 for r in members)
    check(f"{lo}-{hi}" in labels, f"legend address range for {g}", f"{lo}-{hi}")
    check(f"QTY {len(members)}" in labels, f"legend quantity for {g}", str(len(members)))

# patch table rows
table_addr = [t for t in texts if re.fullmatch(r"\d+ - \d+", t[0])]
check(len(table_addr) == 41, "patch table lists 41 address rows", str(len(table_addr)))
table_pairs = sorted((int(t[0].split(" - ")[0]), int(t[0].split(" - ")[1])) for t in table_addr)
want_pairs = sorted((r["address"], r["address"] + r["channels"] - 1) for r in data)
check(table_pairs == want_pairs, "patch table addresses match the plan", "mismatch")
modes = [t for t in texts if re.fullmatch(r"\d+CH", t[0])]
check(len([m for m in modes if m[0] in {f"{r['channels']}CH" for r in data}]) >= 41,
      "patch table carries a mode for every row", str(len(modes)))

# dimensions
dims = {t[0] for t in texts if t[0].endswith(" m")}
check("19.00 m" in dims, "width dimension drawn", "19.00 m")
check("14.72 m" in dims, "depth dimension drawn", "14.72 m")

# title block numbers
alltext = " | ".join(labels)
for field in ["PRESI-PLOT-01", "1:100 @ A3", "1 OF 1", "2026-11-16", "PLAN"]:
    check(field in alltext, f"title block shows {field}")

# everything inside the sheet
outside = [t[0] for t in texts if not (0 <= t[1] <= 420 and 0 <= t[2] <= 297)]
check(not outside, "no text outside the A3 frame", str(outside[:5]))

# collisions among patch-table cells
cells = [t for t in texts if t[4] == "patch"]
def box(t):
    return (t[1], t[2], t[1] + len(t[0]) * t[3] * 0.52, t[2] + t[3])
coll = []
for i in range(len(cells)):
    for j in range(i + 1, len(cells)):
        a, b = box(cells[i]), box(cells[j])
        if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
            coll.append((cells[i][0][:18], cells[j][0][:18]))
check(not coll, "no overlapping patch-table cells", str(coll[:3]))

# plan label collisions
plan_labels = [t for t in texts if t[4] in {"FIX-MOVING", "FIX-RGBW", "FIX-STAGE", "FIX-DJ", "FIX-AURA", "FIX-LASER"}]
clash = []
for i in range(len(plan_labels)):
    for j in range(i + 1, len(plan_labels)):
        a, b = box(plan_labels[i]), box(plan_labels[j])
        if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
            clash.append((plan_labels[i][0], plan_labels[j][0]))
check(not clash, "no overlapping fixture labels on the plan", f"{len(clash)} pairs: {clash[:4]}")

# every symbol sits at its recovered position
PLAN_CX, PLAN_CY, PLAN_SCALE = 150, 178, 0.01
xs = [r["x"] * 1000 for r in data]; zs = [r["z"] * 1000 for r in data]
cxR = (min(xs) + max(xs)) / 2; czR = (min(zs) + max(zs)) / 2
def paper(x, z):
    return (PLAN_CX + x * PLAN_SCALE, PLAN_CY + z * PLAN_SCALE)
sym_pts = {(round(e.dxf.center.x, 2), round(e.dxf.center.y, 2)) for e in circles if e.dxf.center.y > 60}

def square_centres():
    horiz = [e for e in lines if abs(e.dxf.start.y - e.dxf.end.y) < 0.01 and e.dxf.start.y > 60]
    out = set()
    for e in horiz:
        y = round(e.dxf.start.y, 2)
        x0, x1 = sorted((round(e.dxf.start.x, 2), round(e.dxf.end.x, 2)))
        if abs((x1 - x0) - 3.4) < 0.05:
            out.add((round((x0 + x1) / 2, 2), round(y + 1.7, 2)))
    return out

horiz = [e for e in lines if abs(e.dxf.start.y - e.dxf.end.y) < 0.01 and e.dxf.start.y > 60]
def has_edge(cx, y, width):
    for e in horiz:
        if abs(e.dxf.start.y - y) < 0.06:
            x0, x1 = sorted((e.dxf.start.x, e.dxf.end.x))
            if abs((x1 - x0) - width) < 0.08 and abs((x0 + x1) / 2 - cx) < 0.08:
                return True
    return False

bad_pos = []
for r in data:
    wx, wy = paper(r["x"] * 1000, r["z"] * 1000)
    want = (round(wx, 2), round(wy, 2))
    if r["kind"] == "head" or r["group"] in ("Aura", "Laser"):
        ok = want in sym_pts
    elif r["group"] == "DJ World Beams":
        ok = has_edge(wx, wy - 1.19, 3.4)
    else:
        ok = has_edge(wx, wy - 1.7, 3.4)
    if not ok:
        bad_pos.append(f"{r['name']} ({r['group']}) expected {want}")
check(not bad_pos, "every symbol sits at its recovered position", str(bad_pos[:3]))

# aura and laser paint a second, inner circle at the same centre
for group, layer in (("Aura", "FIX-AURA"), ("Laser", "FIX-LASER")):
    members = [r for r in data if r["group"] == group]
    for r in members:
        want = tuple(round(v, 2) for v in paper(r["x"] * 1000, r["z"] * 1000))
        n = sum(1 for e in circles
                if e.dxf.layer == layer
                and (round(e.dxf.center.x, 2), round(e.dxf.center.y, 2)) == want)
        check(n == 2, f"{group} {r['name']} drawn as a double circle", f"{n} circles at its centre")

# patch table rows carry name, model, address, mode together
row_y = {}
for txt, x, y, h, layer in texts:
    if layer == "patch":
        row_y.setdefault(round(y, 1), []).append((x, txt))
rows_ok = 0
for y, cells in row_y.items():
    joined = " ".join(t for _, t in sorted(cells))
    if re.search(r"\d+ - \d+", joined) and "CH" in joined:
        rows_ok += 1
check(rows_ok == 41, "patch table rows are complete on one line each", str(rows_ok))

# room rectangle is the edited size
room_want = (190.0, 147.2)
rect_edges = [e for e in lines if e.dxf.layer == "border"]
widths = sorted({round(abs(e.dxf.end.x - e.dxf.start.x), 2) for e in rect_edges if abs(e.dxf.end.y - e.dxf.start.y) < 0.01})
check(any(abs(w - room_want[0]) < 0.6 for w in widths), "room width matches the building value", str(widths[:6]))
heights = sorted({round(abs(e.dxf.end.y - e.dxf.start.y), 2) for e in rect_edges if abs(e.dxf.end.x - e.dxf.start.x) < 0.01})
check(any(abs(h - room_want[1]) < 0.6 for h in heights), "room depth matches the building value", str(heights[:6]))

# scale bar: five one-metre blocks = 50 mm
bar = [e for e in lines if e.dxf.layer == "dim" and abs(e.dxf.end.y - e.dxf.start.y) < 0.01
       and abs(abs(e.dxf.end.x - e.dxf.start.x) - 10) < 0.3]
check(len(bar) >= 5, "scale bar has five 10 mm blocks (5 m at 1:100)", f"{len(bar)} blocks")

# shape-level assertions, not just line counts
diag = []
for r in data:
    if r["group"] != "Stage Panels":
        continue
    wx, wy = paper(r["x"] * 1000, r["z"] * 1000)
    found = any(abs(abs(e.dxf.end.x - e.dxf.start.x) - abs(e.dxf.end.y - e.dxf.start.y)) < 0.05
                and abs(e.dxf.end.y - e.dxf.start.y) > 1.0
                and abs((e.dxf.start.x + e.dxf.end.x) / 2 - wx) < 0.1
                and abs((e.dxf.start.y + e.dxf.end.y) / 2 - wy) < 0.1
                for e in lines)
    if not found:
        diag.append(r["name"])
check(not diag, "every stage panel carries its diagonal", str(diag[:4]))

nodiag = []
for r in data:
    if r["group"] != "RGBW Pars":
        continue
    wx, wy = paper(r["x"] * 1000, r["z"] * 1000)
    found = any(abs(abs(e.dxf.end.x - e.dxf.start.x) - abs(e.dxf.end.y - e.dxf.start.y)) < 0.05
                and abs(e.dxf.end.y - e.dxf.start.y) > 1.0
                and abs((e.dxf.start.x + e.dxf.end.x) / 2 - wx) < 0.1
                and abs((e.dxf.start.y + e.dxf.end.y) / 2 - wy) < 0.1
                for e in lines)
    if found:
        nodiag.append(r["name"])
check(not nodiag, "pars stay plain squares", str(nodiag[:4]))

beams_bad = []
for r in data:
    if r["group"] != "DJ World Beams":
        continue
    wx, wy = paper(r["x"] * 1000, r["z"] * 1000)
    top = any(abs(e.dxf.start.y - (wy + 1.19)) < 0.06 and abs(abs(e.dxf.end.x - e.dxf.start.x) - 3.4) < 0.08
              for e in horiz)
    if not top:
        beams_bad.append(r["name"])
check(not beams_bad, "beams are drawn flatter than pars (3.4 x 2.38 mm)", str(beams_bad[:4]))

# ---------------------------------------------------------------- report
width = max(len(n[1]) for n in notes)
for ok, label, detail in notes:
    mark = "PASS" if ok else "FAIL"
    print(f"{mark}  {label.ljust(width)}  {detail}")
print()
print(f"{len(notes)} checks, {len(problems)} failures")
sys.exit(1 if problems else 0)
