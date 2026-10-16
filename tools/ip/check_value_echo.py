#!/usr/bin/env python3
"""Fail if a faction value equals the WC3 analogue value it was meant to move away from.

Usage: python3 tools/ip/check_value_echo.py [--reference FILE] [--data DIR]

The reference table (default tools/ip/value_echo_reference.json) is hand-entered from wiki reading, never from game files
(docs/research/ip-safety.md §2.7). Each entry names one of our defs, a dotted field path, our design value ("ours") and the
WC3 analogue value ("ref"). Two checks run:

1. Design check: every entry's "ours" must differ from its "ref" (unless the entry is marked "exempt" with a reason).
2. Data check: when the def exists in data/*.json, the value at the field path must differ from "ref" (an error), and should
   equal "ours" (a warning when it drifts from the design doc).

Global rules (food cap, hero cost, upkeep tiers, the XP table) are not listed and so never flagged.
Exit code 1 when any error is found.
"""
import argparse
import json
import pathlib
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

    exempt_n = sum(1 for e in entries if e.get("exempt"))
    print(f"Value-echo check: {len(entries)} entries ({exempt_n} exempt), {checked_data} found in data, "
          f"{errors} error(s), {warnings} warning(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
