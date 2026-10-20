#!/usr/bin/env python3
"""Listen-check exported voice lines by measurement: transcribe each .ogg and compare it with the script line.

Needs faster-whisper (not a game dependency): python3 -m venv /tmp/asr && /tmp/asr/bin/pip install faster-whisper,
then run this file with that interpreter. The model (default small.en) downloads from the Hugging Face hub once.

  vo_asr_check.py --jobs 10192392,2f1c...      check every exported line of these logged jobs (tools/prompts/vo/vo_jobs.json)
  vo_asr_check.py --speaker hodman             check every exported line of one speaker
  vo_asr_check.py --all                        every speaker
  --json report.json                           also write the rows as JSON

A row is flagged when the word similarity (difflib ratio of normalised words) is below --min-ratio (default 0.6):
that is a merged or split take, a wrong line in the slot, or a mispronunciation worth a listen. Invented names and
interjections ("Hm-hm", "Mm") are normalised away before the comparison.
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPT = os.path.join(ROOT, "tools/prompts/vo/vo_script.json")
JOBS = os.path.join(ROOT, "tools/prompts/vo/vo_jobs.json")
OUT = os.path.join(ROOT, "assets/audio/voice")
FILLERS = {"hm", "hmm", "mm", "mmm", "hmhm", "uh", "um", "oh", "ooh", "eh"}


def norm(t):
    t = t.lower().replace("…", " ").replace("-", "")
    ws = re.findall(r"[a-z0-9']+", t)
    return [w.strip("'") for w in ws if w.strip("'") not in FILLERS]


def load_audio(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         stdout=subprocess.PIPE, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def targets(script, jobs, speakers=None, job_ids=None):
    rows = []
    if job_ids:
        for j in jobs:
            if any(j["job_id"].startswith(k) for k in job_ids):
                spk = script["speakers"][j["speaker"]]
                for n in sorted(set(j["lines"])):
                    rows.append((j["speaker"], spk["faction"], j["category"], n, spk["lines"][j["category"]][n - 1]))
        return rows
    for sk, spk in script["speakers"].items():
        if speakers and sk not in speakers:
            continue
        for cat, lines in spk["lines"].items():
            for n, ln in enumerate(lines, 1):
                rows.append((sk, spk["faction"], cat, n, ln))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs")
    ap.add_argument("--speaker")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--model", default="small.en")
    ap.add_argument("--min-ratio", type=float, default=0.6)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    from faster_whisper import WhisperModel
    script = json.load(open(SCRIPT, encoding="utf-8"))
    jobs = json.load(open(JOBS, encoding="utf-8")) if os.path.exists(JOBS) else []
    rows = targets(script, jobs, [a.speaker] if a.speaker else None, a.jobs.split(",") if a.jobs else None)
    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    out = []
    bad = 0
    for sk, fac, cat, n, text in rows:
        path = os.path.join(OUT, fac, sk, f"{cat}_{n:02d}.ogg")
        if not os.path.exists(path):
            continue
        segs, _ = model.transcribe(load_audio(path), beam_size=5, language="en", vad_filter=False,
                                   initial_prompt=text if False else None)
        heard = " ".join(s.text.strip() for s in segs)
        r = difflib.SequenceMatcher(None, norm(text), norm(heard)).ratio()
        flag = r < a.min_ratio
        bad += flag
        out.append({"file": os.path.relpath(path, ROOT), "text": text, "heard": heard, "ratio": round(r, 2), "flag": flag})
        print(f"{'FLAG' if flag else 'ok  '} {r:4.2f}  {sk}/{cat}_{n:02d}  script: {text!r}  heard: {heard!r}")
    if a.json:
        with open(a.json, "w") as f:
            json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"checked {len(out)} line(s), flagged {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
