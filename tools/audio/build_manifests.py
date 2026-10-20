#!/usr/bin/env python3
"""Write assets/audio/sfx/manifest.json and assets/audio/music/manifest.json from the files on disk.

SFX: every assets/audio/sfx/<group>/<stem>_<nn>.wav becomes {"<stem>": ["res://assets/audio/sfx/<group>/<stem>_01.wav", ...]}.
Kit items keep their own ids (ui_order_kingdom_move, bullet_hit_wood, ...). Ids listed in AGGREGATES also get a parent
key holding all their children (material variants a caller may pick at random).

Music: assets/audio/music/*.ogg, with the metadata in tools/audio/music_jobs.json ("result" entries written by the
post step): {"<piece id>": {"file": "res://...", "length_s": ..., "prompt_id": ..., "job_id": ..., "music_length_ms": ...}}.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
AGGREGATES = ["bullet_hit", "javelin_hit"]


def sfx():
    root = os.path.join(REPO, "assets", "audio", "sfx")
    out = {}
    for group in sorted(os.listdir(root)):
        gdir = os.path.join(root, group)
        if not os.path.isdir(gdir):
            continue
        for fn in sorted(os.listdir(gdir)):
            m = re.match(r"^(.+)_(\d\d)\.wav$", fn)
            if not m:
                continue
            out.setdefault(m.group(1), []).append("res://assets/audio/sfx/%s/%s" % (group, fn))
    for parent in AGGREGATES:
        kids = sorted(k for k in out if k.startswith(parent + "_"))
        if kids and parent not in out:
            out[parent] = [p for k in kids for p in out[k]]
    out = dict(sorted(out.items()))
    with open(os.path.join(root, "manifest.json"), "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    print("sfx manifest: %d ids, %d files" % (len(out), sum(len(v) for k, v in out.items() if k not in AGGREGATES)))


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       stdout=subprocess.PIPE, text=True)
    return round(float(r.stdout.strip()), 2)


def music():
    root = os.path.join(REPO, "assets", "audio", "music")
    jobs = json.load(open(os.path.join(HERE, "music_jobs.json")))["jobs"]
    out = {}
    for j in jobs:
        res = j.get("result")
        if not res:
            continue
        path = os.path.join(REPO, res["file"])
        if not os.path.exists(path):
            print("missing", path, file=sys.stderr)
            continue
        out[j["id"]] = {
            "piece": j["piece"],
            "file": "res://" + res["file"],
            "length_s": duration(path),
            "prompt_id": j["prompt_id"],
            "job_id": res.get("job_id"),
            "music_length_ms_sent": res.get("music_length_ms_sent", j["music_length_ms"]),
            "music_length_ms_bible": j["music_length_ms"],
            "kind": j["kind"],
        }
    with open(os.path.join(root, "manifest.json"), "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("music manifest: %d pieces" % len(out))


if __name__ == "__main__":
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__)
        sys.exit(0)
    sfx()
    music()
