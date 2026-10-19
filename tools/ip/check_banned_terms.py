#!/usr/bin/env python3
"""Fail if any banned IP term appears in shipped content, data, asset names or prompts.

Usage: python3 tools/ip/check_banned_terms.py [paths...]
  (default: src data assets tests tools/prompts docs/design/art-and-audio-bible.md)
Exit code 1 when a match is found. Docs under docs/ are exempt (research and design notes compare against WC3 on purpose),
except the art-and-audio bible: generation prompts are assembled from it, so it is checked like shipped content.

A second pass applies banned_ui_terms.txt to the string table (data/strings/) only: player-facing labels that must not appear in UI
text although the matching code or data id (e.g. `true_sight`) is legal (docs/design/rules.md §10.7).
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TERMS_FILE = pathlib.Path(__file__).with_name("banned_terms.txt")
UI_TERMS_FILE = pathlib.Path(__file__).with_name("banned_ui_terms.txt")
UI_PATHS = ["data/strings"]
DEFAULT_PATHS = ["src", "data", "assets", "tests", "tools/prompts", "docs/design/art-and-audio-bible.md"]
TEXT_EXT = {".gd", ".json", ".tscn", ".tres", ".md", ".txt", ".csv", ".cfg", ".py", ".gdshader", ".godot"}
# Words that are legitimate in game rules text: only flag them as whole proper names elsewhere.
ALLOWED_CONTEXT = {"grunt": re.compile(r"\bgrunts? (?:sfx|sound|vocal)", re.I)}


def load_terms(path: pathlib.Path = TERMS_FILE) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [ln.strip().lower() for ln in lines if ln.strip() and not ln.startswith("#")]


def compile_terms(terms: list[str]) -> list:
    return [(t, re.compile(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", re.I)) for t in terms]


def main(argv: list[str]) -> int:
    patterns = compile_terms(load_terms())
    paths = [ROOT / p for p in (argv or DEFAULT_PATHS)]
    hits = scan(paths, patterns)
    # UI-string pass: the string table only (with explicit paths, only those inside a UI path).
    ui_roots = [ROOT / p for p in UI_PATHS]
    if argv:
        ui_scan = [p for p in paths if any(p == u or u in p.parents for u in ui_roots)]
    else:
        ui_scan = ui_roots
    hits += scan(ui_scan, compile_terms(load_terms(UI_TERMS_FILE)), label="banned UI term")
    if hits:
        print(f"\n{hits} banned-term hit(s). See docs/research/ip-safety.md §2.")
        return 1
    print("IP check: no banned terms found.")
    return 0


def scan(paths: list, patterns: list, label: str = "banned term") -> int:
    hits = 0
    for base in paths:
        if not base.exists():
            continue
        files = [base] if base.is_file() else [f for f in base.rglob("*") if f.is_file()]
        for f in files:
            rel = f.relative_to(ROOT).as_posix()
            if rel.startswith("tools/ip/"):
                continue
            for term, pat in patterns:  # file names
                if pat.search(f.name.replace("_", " ")):
                    print(f"{rel}: {label} in filename: {term}")
                    hits += 1
            if f.suffix.lower() not in TEXT_EXT:
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            for n, line in enumerate(text.splitlines(), 1):
                for term, pat in patterns:
                    if pat.search(line):
                        ctx = ALLOWED_CONTEXT.get(term)
                        if ctx and ctx.search(line):
                            continue
                        print(f"{rel}:{n}: {label} '{term}': {line.strip()[:120]}")
                        hits += 1
    return hits


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
