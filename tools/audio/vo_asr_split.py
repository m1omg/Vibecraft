#!/usr/bin/env python3
"""Find where each script line starts in a batched TTS take by speech recognition, and print the cut times.

Some voices pause longer inside a line ("Slowly. Surely.") than between lines, so the pause-length split of
vo_split.py can merge two lines or break one. This tool transcribes the raw take with word timestamps
(faster-whisper, default medium.en), aligns the recognised words with the script words of the job's lines, and puts
each cut in the middle of the quietest stretch between the last word of one line and the first word of the next.

  vo_asr_split.py JOB_ID            print the cut times (seconds) and the words of each line
  vo_asr_split.py JOB_ID --apply    also re-run `vo_tool.py process JOB_ID --cuts ...`

Needs faster-whisper (see vo_asr_check.py); run it with that interpreter. Nothing is paid for: it only re-cuts
the take already downloaded to assets_src/.
"""
import argparse
import difflib
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import vo_split  # noqa: E402
from vo_asr_check import norm, load_audio, SCRIPT, JOBS  # noqa: E402


def job_items(j):
    return [tuple(x) for x in j["items"]] if "items" in j else [(j["category"], n) for n in j["lines"]]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job_id")
    ap.add_argument("--model", default="medium.en")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--noise-db", type=float, default=-40.0)
    a = ap.parse_args(argv)
    from faster_whisper import WhisperModel
    script = json.load(open(SCRIPT, encoding="utf-8"))
    jobs = json.load(open(JOBS, encoding="utf-8"))
    job = next(j for j in jobs if j["job_id"].startswith(a.job_id))
    spk = script["speakers"][job["speaker"]]
    texts = [spk["lines"][c][n - 1] for c, n in job_items(job)]
    raw = os.path.join(ROOT, job["raw"])
    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(load_audio(raw), beam_size=5, language="en", word_timestamps=True, vad_filter=False,
                               initial_prompt=" ".join(texts))
    heard = []
    for s in segs:
        for w in s.words:
            for t in norm(w.word):
                heard.append((t, w.start, w.end))
    exp = []
    for k, t in enumerate(texts):
        exp += [(w, k) for w in norm(t)]
    sm = difflib.SequenceMatcher(None, [w for w, _ in exp], [w for w, _, _ in heard], autojunk=False)
    line_of = [None] * len(heard)
    for blk in sm.get_matching_blocks():
        for i in range(blk.size):
            line_of[blk.b + i] = exp[blk.a + i][1]
    # fill unmatched heard words from their neighbours
    last = 0
    for i in range(len(line_of)):
        if line_of[i] is None:
            line_of[i] = last
        last = line_of[i]
    x = vo_split.decode(raw)
    edb = vo_split.env_db(x)
    hop_s = vo_split.HOP / vo_split.SR
    cuts = []
    for k in range(len(texts) - 1):
        ends = [e for (w, s, e), l in zip(heard, line_of) if l == k]
        starts = [s for (w, s, e), l in zip(heard, line_of) if l == k + 1]
        if not ends or not starts:
            print(f"line {k + 1}/{k + 2}: no words recognised, cannot place the cut", file=sys.stderr)
            return 2
        lo, hi = max(ends) - 0.12, min(starts) + 0.12
        lo_f, hi_f = max(0, int(lo / hop_s)), min(len(edb) - 1, int(hi / hop_s))
        if hi_f <= lo_f:
            hi_f = lo_f + 1
        win = edb[lo_f:hi_f]
        quiet = win < a.noise_db
        # middle of the longest quiet run in the window, else the quietest frame
        best, run, best_mid = 0, 0, None
        for i, q in enumerate(quiet):
            run = run + 1 if q else 0
            if run > best:
                best, best_mid = run, i - run // 2
        idx = best_mid if best_mid is not None else int(np.argmin(win))
        cuts.append(round((lo_f + idx) * hop_s, 3))
    for k, t in enumerate(texts):
        ws = " ".join(w for (w, s, e), l in zip(heard, line_of) if l == k)
        print(f"line {k + 1}: script {t!r}  heard {ws!r}")
    print("cuts:", ",".join(f"{c:.3f}" for c in cuts))
    if a.apply:
        r = subprocess.run([sys.executable if False else "python3", os.path.join(HERE, "vo_tool.py"), "process", job["job_id"],
                            "--cuts", ",".join(f"{c:.3f}" for c in cuts)])
        return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
