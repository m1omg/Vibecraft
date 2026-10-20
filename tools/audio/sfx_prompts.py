#!/usr/bin/env python3
"""Build Seed Audio prompts from the fixed wrappers of the art-and-audio bible (section 9.1).

The job table (default: tools/audio/sfx_jobs.json) lists one entry per generation job:

    {"id": "hit_metal_l", "group": "combat", "w": "O", "n": 4, "d": 0.5,
     "clause": "a blade striking blackened iron plate ...", "p": "P0"}

Wrapper codes: O one-shot, L loop, V vocal set, A ambience, S stinger, K kit set.
  O: needs clause, n, d            L / A / S: clause, d
  V: needs voice, list, n          K: needs list (numbered string), t (default 2)

Usage:
  sfx_prompts.py ID [ID ...]        print the prompt(s) for these job ids
  sfx_prompts.py --all              print every prompt with its id and length
  sfx_prompts.py --check            verify every prompt is <= 2048 chars and has no banned term
  sfx_prompts.py --jobs FILE ...    use another job table

The prompt text is the single source of truth for the ledger: the ledger names the job id
and this table holds the exact prompt that was sent.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

WRAPPERS = {
    "O": ("Sound effect only. No music, no speech, no background ambience. [sound: {clause}] {n} separate variations, each "
          "about {d} seconds, separated by about half a second of silence. Each variation slightly different in pitch and texture. Dry, "
          "punchy, stylized fantasy game sound, close-miked."),
    "L": ("Sound effect only. No music, no speech, no background. [sound: {clause}] One continuous take of about {d} seconds "
          "with even density and no sudden events, so it can loop seamlessly."),
    "V": ("Creature sound effects only. No music, no words, no background. [voice: {voice}] {list}. {n} separate sounds, "
          "separated by about half a second of silence."),
    "A": ("Ambient soundscape only. No music, no speech. [background: {clause}] About {d} seconds, even density for seamless "
          "looping, no sudden loud events."),
    "S": ("Sound effect only. No melody, no speech. [sound: {clause}] One take of about {d} seconds with a natural decay."),
    "K": ("Sound effects only. No music, no speech, no background. [sound: a set of related small interface sounds] {list}, in this "
          "order, each sound made {t} times with slight variation. All separated by about half a second of silence. Dry, close-miked, stylized "
          "fantasy game sounds."),
}


def fmt_num(x):
    if isinstance(x, (int, float)):
        s = ("%.2f" % x).rstrip("0").rstrip(".")
        return "1.0" if s == "1" else s
    return str(x)


def build(job):
    w = job["w"]
    if w not in WRAPPERS:
        raise ValueError("%s: unknown wrapper %r" % (job["id"], w))
    fields = {
        "clause": job.get("clause", ""),
        "n": job.get("n", ""),
        "d": fmt_num(job.get("d", "")),
        "voice": job.get("voice", ""),
        "list": job.get("list", ""),
        "t": job.get("t", 2),
    }
    return WRAPPERS[w].format(**fields)


def load(path):
    with open(path) as f:
        data = json.load(f)
    return data["jobs"] if isinstance(data, dict) else data


def banned_terms():
    terms = []
    p = os.path.join(REPO, "tools", "ip", "banned_terms.txt")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#"):
                terms.append(line.lower())
    return terms


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--jobs", default=os.path.join(HERE, "sfx_jobs.json"))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true", help="print {id: prompt} as JSON")
    a = ap.parse_args()
    jobs = load(a.jobs)
    by_id = {j["id"]: j for j in jobs}
    if a.check:
        bad = 0
        terms = banned_terms()
        for j in jobs:
            p = build(j)
            if len(p) > 2048:
                print("TOO LONG %s %d" % (j["id"], len(p)))
                bad += 1
            low = p.lower()
            for t in terms:
                if re.search(r"\b%s\b" % re.escape(t), low):
                    print("BANNED %s: %s" % (j["id"], t))
                    bad += 1
        print("%d jobs checked, %d problems" % (len(jobs), bad))
        sys.exit(1 if bad else 0)
    sel = jobs if a.all or not a.ids else [by_id[i] for i in a.ids]
    if a.json:
        print(json.dumps({j["id"]: build(j) for j in sel}, indent=1))
        return
    for j in sel:
        p = build(j)
        if a.all:
            print("## %s (%s, %d chars)" % (j["id"], j["w"], len(p)))
        print(p)


if __name__ == "__main__":
    main()
