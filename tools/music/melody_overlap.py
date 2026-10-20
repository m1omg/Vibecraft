#!/usr/bin/env python3
"""melody_overlap.py: how much melody do two pieces share? (a self-check for a faction's rotation)

For every melodic track of every piece given, the top line (one note per onset) is turned into scale-degree
intervals in that piece's own mode, ignoring rhythm and octave register, so a theme that was slowed down,
re-barred or moved to another mode still matches. The longest common run of intervals is reported for every
pair of tracks from DIFFERENT pieces, with the bars where it starts. A shared run of N intervals = N + 1 notes.

The faction motif itself is 5 notes (4 intervals) and is meant to be shared; the target for a rotation is no
shared run longer than the motif plus one note (6 notes = 5 intervals). A rest of `--gap` beats or more (default 1)
ends a phrase, and runs never cross a phrase end. Purely stepwise runs (every interval one scale step, up or
down) are generic melodic motion; they are reported separately and not counted against the target.

  python3 tools/music/melody_overlap.py clans_1 clans_2 clans_3
  python3 tools/music/melody_overlap.py clans_1 clans_2 clans_3 --tracks two_string,two_string_high,lute_lead
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

DEFAULT_TRACKS = ("two_string", "two_string_high", "lute_lead", "horn_high", "horn", "fiddle", "viola")


def load(name):
    path = name if name.endswith(".py") else os.path.join(HERE, "pieces", f"{name}.py")
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    p = m.build()
    p.compile()
    return p


def top_line(track):
    ns = sorted(track.notes, key=lambda x: (x.beat, -x.pitch))
    line = []
    for x in ns:
        if line and abs(line[-1].beat - x.beat) < 1e-6:
            continue
        line.append(x)
    return line


BREAK = 99   # interval placeholder at a phrase end: never equal across pieces (made unique per position)


def lines(p, names, gap=1.0):
    out = {}
    for k, t in p.tracks.items():
        if k not in names or not t.notes:
            continue
        ln = top_line(t)
        degs = [p.mode.degree_of(x.pitch)[0] for x in ln]
        iv = []
        for i in range(len(degs) - 1):
            rest = ln[i + 1].beat - (ln[i].beat + ln[i].dur)
            iv.append((BREAK, id(p), k, i) if rest >= gap - 1e-6 else degs[i + 1] - degs[i])
        out[k] = (ln, iv)
    return out


def generic(run):
    return all(abs(s) == 1 for s in run)


def common_runs(a, b, min_len=5):
    """All maximal common runs (len >= min_len) between interval lists a and b: (len, i, j)."""
    na, nb = len(a), len(b)
    dp = [[0] * (nb + 1) for _ in range(na + 1)]
    for i in range(1, na + 1):
        for j in range(1, nb + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
    res = []
    for i in range(1, na + 1):
        for j in range(1, nb + 1):
            L = dp[i][j]
            ends = i == na or j == nb or a[i] != b[j]       # maximal: the run does not continue
            if L >= min_len and ends:
                res.append((L, i - L, j - L))
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pieces", nargs="+")
    ap.add_argument("--tracks", default=",".join(DEFAULT_TRACKS), help="comma-separated melodic track names")
    ap.add_argument("--target", type=int, default=5, help="max shared intervals allowed (default 5 = 6 notes)")
    ap.add_argument("--gap", type=float, default=1.0, help="a rest of this many beats ends a phrase")
    ap.add_argument("--json", help="write the result here")
    a = ap.parse_args()
    names = set(a.tracks.split(","))
    P = {nm: load(nm) for nm in a.pieces}
    L = {nm: lines(p, names, a.gap) for nm, p in P.items()}
    report, worst = [], 0
    keys = list(P)
    for x in range(len(keys)):
        for y in range(x + 1, len(keys)):
            pa, pb = keys[x], keys[y]
            best = None
            for ta, (la, ia) in L[pa].items():
                for tb, (lb, ib) in L[pb].items():
                    for n_, i, j in common_runs(ia, ib, min_len=4):
                        run = ia[i:i + n_]
                        g = generic(run)
                        item = {"len_intervals": n_, "notes": n_ + 1, "generic_scale_run": g,
                                "a": [pa, ta, round(P[pa].bar_index(la[i].beat) + 1, 2)],
                                "b": [pb, tb, round(P[pb].bar_index(lb[j].beat) + 1, 2)], "intervals": run}
                        if not g and (best is None or n_ > best["len_intervals"]):
                            best = item
                        if n_ > a.target:
                            report.append(item)
            if best:
                worst = max(worst, best["len_intervals"])
            print(f"{pa} x {pb}: longest shared non-scale run "
                  f"{best['notes'] if best else 0} notes ({best['len_intervals'] if best else 0} intervals)"
                  + (f"  {best['a'][1]} bar {best['a'][2]} / {best['b'][1]} bar {best['b'][2]} {best['intervals']}"
                     if best else ""))
    over = [r for r in report if not r["generic_scale_run"]]
    for r in sorted(over, key=lambda r: -r["len_intervals"])[:20]:
        print(f"  OVER: {r['notes']} notes  {r['a']}  {r['b']}  {r['intervals']}")
    gen = [r for r in report if r["generic_scale_run"]]
    if gen:
        print(f"  (generic scale runs longer than the target: {len(gen)}, not counted)")
    ok = worst <= a.target
    print("PASS" if ok else "FAIL", f"(worst {worst + 1 if worst else 0} notes, target <= {a.target + 1})")
    if a.json:
        json.dump({"worst_intervals": worst, "over": over, "generic": gen}, open(a.json, "w"), indent=1)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
