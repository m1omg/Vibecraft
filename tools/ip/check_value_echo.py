#!/usr/bin/env python3
"""Fail if a faction value equals the WC3 analogue value it was meant to move away from.

Usage: python3 tools/ip/check_value_echo.py [--reference FILE] [--data DIR]

The reference table (default tools/ip/value_echo_reference.json) is hand-entered from wiki reading, never from game files
(docs/research/ip-safety.md §2.7). Each entry names one of our defs, a dotted field path, our design value ("ours") and the
WC3 analogue value ("ref"). Two checks run:

1. Design check: every entry's "ours" must differ from its "ref" (unless the entry is marked "exempt" with a reason).
2. Data check: when the def exists in data/*.json, the value at the field path must differ from "ref" (an error), and should
   equal "ours" (a warning when it drifts from the design doc).

3. Team colours (the "team_colours" block): every design colour, and every Color(r, g, b) literal in the COLORS array of the
   block's "code_file", must be at least "threshold_de76" (CIE76) from every reference player colour (art-and-audio bible §2.4).

Global rules (food cap, hero cost, upkeep tiers, the XP table) are not listed and so never flagged.
Exit code 1 when any error is found.
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_REFERENCE = pathlib.Path(__file__).with_name("value_echo_reference.json")


def load_defs(data_dir: pathlib.Path) -> dict:
    defs = {}
    for f in sorted(data_dir.glob("*.json")):
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"{f.relative_to(ROOT)}: cannot parse JSON ({e})")
            continue
        if isinstance(doc, dict):
            for key, val in doc.items():
                if isinstance(val, dict):
                    defs.setdefault(key, val)
    return defs


def get_path(obj, dotted: str):
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def same(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) < 1e-9
    return a == b


def _lab(rgb) -> tuple:
    """sRGB 0-255 -> CIE Lab (D65)."""
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(float(c)) for c in rgb)
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883

    def f(t):
        return t ** (1.0 / 3.0) if t > 0.008856 else 7.787 * t + 16.0 / 116.0
    fx, fy, fz = f(x), f(y), f(z)
    return (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


def delta_e76(a, b) -> float:
    la, lb = _lab(a), _lab(b)
    return sum((p - q) ** 2 for p, q in zip(la, lb)) ** 0.5


def _hex_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def code_colours(path: pathlib.Path) -> list:
    """Color(r, g, b[, a]) float literals inside the first `COLORS` array of a GDScript file, as 0-255 tuples."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    m = re.search(r"COLORS[^=]*=\s*\[(.*?)\]", text, re.S)
    if not m:
        return []
    out = []
    for c in re.finditer(r"Color\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)", m.group(1)):
        out.append(tuple(round(float(v) * 255) for v in c.groups()))
    return out


def check_team_colours(block: dict) -> int:
    """Return the number of errors: any colour within the threshold of a reference player colour."""
    if not block:
        return 0
    thr = float(block.get("threshold_de76", 15))
    refs = {k: tuple(v) for k, v in block.get("ref", {}).items()}
    errors = 0
    candidates = [(f"design {name}", _hex_rgb(h)) for name, h in block.get("ours", {}).items()]
    code_file = block.get("code_file")
    if code_file:
        for i, rgb in enumerate(code_colours(ROOT / code_file)):
            candidates.append((f"code {code_file} COLORS[{i}]", rgb))
    for label, rgb in candidates:
        dist, nearest = min((delta_e76(rgb, v), k) for k, v in refs.items())
        if dist < thr:
            print(f"ERROR team colour: {label} {rgb} is ΔE {dist:.1f} from the reference '{nearest}' (minimum {thr:g})")
            errors += 1
    return errors


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reference", type=pathlib.Path, default=DEFAULT_REFERENCE)
    ap.add_argument("--data", type=pathlib.Path, default=ROOT / "data")
    args = ap.parse_args(argv)

    ref_doc = json.loads(args.reference.read_text(encoding="utf-8"))
    entries = ref_doc.get("entries", [])
    defs = load_defs(args.data)
    errors = warnings = checked_data = 0

    for e in entries:
        name = f"{e['def']}.{e['field']}"
        exempt = e.get("exempt")
        if "ours" in e and same(e["ours"], e["ref"]) and not exempt:
            print(f"ERROR design: {name} = {e['ours']} equals the WC3 {e.get('analogue', 'analogue')} value {e['ref']}")
            errors += 1
        if e["def"] in defs:
            val = get_path(defs[e["def"]], e["field"])
            if val is None:
                continue
            checked_data += 1
            if same(val, e["ref"]) and not exempt:
                print(f"ERROR data: {name} = {val} equals the WC3 {e.get('analogue', 'analogue')} value {e['ref']}")
                errors += 1
            elif "ours" in e and not same(val, e["ours"]):
                print(f"warning data: {name} = {val}, but the design doc says {e['ours']}")
                warnings += 1

    tc_errors = check_team_colours(ref_doc.get("team_colours", {}))
    errors += tc_errors

    exempt_n = sum(1 for e in entries if e.get("exempt"))
    print(f"Value-echo check: {len(entries)} entries ({exempt_n} exempt), {checked_data} found in data, "
          f"{tc_errors} team-colour error(s), {errors} error(s) in all, {warnings} warning(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
