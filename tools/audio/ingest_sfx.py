#!/usr/bin/env python3
"""Download a finished Seed Audio job and split it into takes with split_takes.py.

  ingest_sfx.py ID JOB_ID URL [--dry-run] [split_takes options ...]

Looks the job up in tools/audio/sfx_jobs.json (group, n, d), saves the raw file as
assets_src/audio/sfx/<group>/<id>__<job8>.<ext> (skips the download if it is already there),
writes the take report next to it and exports the takes to assets/audio/sfx/<group>/.
Extra options are passed through to split_takes.py (e.g. --reject 2, --names a,b, --thresh-db -30).
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))


def main():
    if len(sys.argv) < 4 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    sid, job, url = sys.argv[1:4]
    extra = sys.argv[4:]
    jobs = {j["id"]: j for j in json.load(open(os.path.join(HERE, "sfx_jobs.json")))["jobs"]}
    j = jobs[sid]
    group = j["group"]
    ext = os.path.splitext(url.split("?")[0])[1] or ".mp3"
    raw_dir = os.path.join(REPO, "assets_src", "audio", "sfx", group)
    os.makedirs(raw_dir, exist_ok=True)
    raw = os.path.join(raw_dir, "%s__%s%s" % (sid, job[:8], ext))
    if not os.path.exists(raw):
        subprocess.run(["curl", "-sS", "--fail", "--max-time", "120", "-o", raw, url], check=True)
    cmd = [sys.executable, os.path.join(HERE, "split_takes.py"), raw, "--id", sid,
           "--out", os.path.join(REPO, "assets", "audio", "sfx", group),
           "--report", raw.rsplit(".", 1)[0] + ".json"]
    if j.get("n"):
        cmd += ["--expect", str(j["n"])]
    if j.get("d"):
        cmd += ["--dur", str(j["d"])]
    subprocess.run(cmd + extra, check=True)


if __name__ == "__main__":
    main()
