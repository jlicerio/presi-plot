#!/usr/bin/env python3
"""Cross-check the sheet against the original show file extraction.

The show file (source_show.json) is the primary source: it holds each fixture's
desk name, address and universe. This compares those with the sheet, and uses the
fixed start addresses to prove the channel widths tile the universe exactly.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
SHOW_CANDIDATES = [
    Path("/Users/selfsim/projects/wmx1-convert-stage-sim/source_show.json"),
    Path("/Users/selfsim/projects/wmx1-convert/source_show.json"),
]
SHOW = next((p for p in SHOW_CANDIDATES if p.exists()), SHOW_CANDIDATES[0])
SHEET = HERE / "data-dump.json"

if not SHOW.exists():
    print(f"show file not found at {SHOW}")
    sys.exit(2)

orig = json.loads(SHOW.read_text())
sheet = json.loads(SHEET.read_text())


def short(name):
    tail = name.split(".")[-1]
    head = name.split(".")[0].lower()
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


origin = {short(f["name"]): f for f in orig["fixtures"]}
rows = {r["name"]: r for r in sheet}

problems = []

if len(origin) != len(rows):
    problems.append(f"fixture count {len(origin)} vs {len(rows)}")
if set(origin) != set(rows):
    problems.append(f"ID sets differ: {sorted(set(origin) ^ set(rows))}")

for name in sorted(set(origin) & set(rows)):
    if origin[name]["address"] != rows[name]["address"]:
        problems.append(f"{name}: address {origin[name]['address']} vs {rows[name]['address']}")
    if int(origin[name]["universe"]) != int(rows[name]["uv"]):
        problems.append(f"{name}: universe {origin[name]['universe']} vs {rows[name]['uv']}")

# the desk's own grouping: one opaque mode blob per model
blobs = defaultdict(set)
for f in orig["fixtures"]:
    blobs[f["mode"]].add(short(f["name"]))
for blob, names in blobs.items():
    groups = {rows[n]["group"] for n in names if n in rows}
    widths = {rows[n]["channels"] for n in names if n in rows}
    if len(groups) != 1 or len(widths) != 1:
        problems.append(f"mode blob spans {groups} / {widths}")

# with starts fixed by the show file, the widths must tile 1..512 exactly
covered = []
for name, r in rows.items():
    covered.append((r["address"], r["address"] + r["channels"] - 1, name))
covered.sort()
for (a0, a1, an), (b0, b1, bn) in zip(covered, covered[1:]):
    if b0 != a1 + 1:
        problems.append(f"gap or overlap between {an} (ends {a1}) and {bn} (starts {b0})")
if covered[0][0] != 1:
    problems.append(f"patch starts at {covered[0][0]}, not 1")
if covered[-1][1] != 512:
    problems.append(f"patch ends at {covered[-1][1]}, not 512")

print(f"show file: {len(origin)} fixtures, {len(blobs)} distinct mode blobs")
print(f"sheet:     {len(rows)} fixtures, channels {covered[0][0]}–{covered[-1][1]}")
print()
if problems:
    print(f"{len(problems)} difference(s):")
    for p in problems:
        print("  " + p)
    sys.exit(1)
print("match: names, addresses, universes, model grouping, and exact channel tiling 1–512.")
