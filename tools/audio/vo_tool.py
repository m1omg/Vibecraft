#!/usr/bin/env python3
"""Voice-over pipeline for the slice: script lint, TTS prompts and costs, job log, post-processing, manifest, docs.

Source of record: tools/prompts/vo/vo_script.json (every line, voice id, tag set and post-chain per speaker).
Job log:          tools/prompts/vo/vo_jobs.json (every paid request: prompt, characters, cost, job id, result).
Raw downloads:    assets_src/audio/voice/<faction>/<speaker>/<category>_<job8>.mp3 (+ .report.json from the split).
Game files:       assets/audio/voice/<faction>/<speaker>/<category>_<nn>.ogg and assets/audio/voice/manifest.json.

Pricing (Krea elevenlabs/tts, measured 2026-10-20 with free preflights): 2/27 CU per prompt character, everything
counted (tags, spaces, newlines). `cost` prints the exact quote of every batch before anything is submitted.

Subcommands:
  lint                                  word budgets, banned words, faction rules (exit 1 on a violation)
  cost  [--speakers a,b] [--cats x,y]   prompt characters and CU per batch (one category of one speaker)
  prompt SPEAKER CAT [--only 1,3]       print the request input JSON (voice_id, model_id, prompt)
  log   SPEAKER CAT JOB_ID [--only ..] [--voice-slot 2] [--status submitted]   append a job to the job log
  set   JOB_ID key=value ...            update a job (status, url, raw, note)
  process JOB_ID [--keep 1,2] [--analyse] [--names ...]   split + post + export one downloaded job
  mix-unison JOB_A JOB_B                (Sling-Cart) split both brothers' takes, mix each line in unison, export
  manifest                              write assets/audio/voice/manifest.json from the files on disk
  doc                                   write docs/design/voice-lines.md from the script, the job log and the files
  spent                                 total CU of all logged jobs (submitted, completed or failed-but-charged)

The separator between lines in one request is SEP (chosen by the probe batch, see voice-lines.md "Generation").
"""
import argparse
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import vo_split  # noqa: E402

SCRIPT = os.path.join(ROOT, "tools/prompts/vo/vo_script.json")
JOBS = os.path.join(ROOT, "tools/prompts/vo/vo_jobs.json")
OUT = os.path.join(ROOT, "assets/audio/voice")
RAW = os.path.join(ROOT, "assets_src/audio/voice")
DOC = os.path.join(ROOT, "docs/design/voice-lines.md")
CU_PER_CHAR = 2.0 / 27.0
MODEL_ID = "eleven_v4"

# Separator between lines inside one request, chosen by the probe batch (hodman what, job 10192392, 2026-10-20):
# "[long pause]" gave a 0.99 s gap, "[pause]" 0.63 s and a bare blank line 0.60 s, against 0.39-0.46 s breaths inside
# two-sentence lines. The splitter uses the N-1 longest pauses for N expected lines and every split is checked with
# speech recognition (tools/audio/vo_asr_check.py), so the 2-character blank line is enough and saves 14 characters
# (1.04 CU) per line against "[long pause]".
SEP = "\n\n"
# Pause inside a line is tightened to at most this many seconds (vo_split --max-gap). Acks must land in 1.4 s.
MAX_GAP = {"what": 0.15, "yes": 0.15, "attack": 0.15, "warcry": 0.15, "need_mana": 0.15, "pack_full": 0.15, "ab_q": 0.15,
           "ab_w": 0.15, "ab_e": 0.15, "ultimate_shout": 0.15, "death_word": 0.35, "annoyed": 0.45}
DEFAULT_GAP = 0.3

CAT_ORDER = ["ready", "what", "yes", "attack", "warcry", "annoyed", "built", "mech", "need_mana", "pack_full", "ab_q",
             "ab_w", "ab_e", "ultimate_shout", "levelup_a", "levelup_6", "rival", "death_word",
             "need_gold", "need_lumber", "need_supply", "hero_slot_full", "cannot_build", "hall_attacked",
             "building_attacked", "units_attacked", "workers_attacked", "hero_in_danger", "hero_fallen", "hero_ready",
             "research_finished", "hall_tier_finished", "mine_low", "mine_exhausted", "upkeep_rises", "no_hall",
             "revealed", "building_finished"]
ADVISOR_CATS = set(CAT_ORDER[CAT_ORDER.index("need_gold"):])
TAG_GROUP = {"what": "ack", "yes": "ack", "ab_q": "ab", "ab_w": "ab", "ab_e": "ab", "ultimate_shout": "warcry",
             "levelup_a": "levelup", "levelup_6": "levelup", "rival": "other", "death_word": "other", "pack_full": "other",
             "need_mana": "need_mana"}
ALERT_CATS = {"hall_attacked", "building_attacked", "units_attacked", "workers_attacked", "hero_in_danger", "no_hall"}

BANNED_WORDS = ["poke", "poked", "poking", "pokes", "tap", "tapped", "tapping", "prod", "jab", "clan", "chieftain",
                "warchief", "milord", "sabre", "saber", "spirits", "omen"]


def load_script():
    with open(SCRIPT, encoding="utf-8") as f:
        return json.load(f)


def load_jobs():
    if not os.path.exists(JOBS):
        return []
    with open(JOBS, encoding="utf-8") as f:
        return json.load(f)


def save_jobs(jobs):
    with open(JOBS, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=1, ensure_ascii=False)
        f.write("\n")


def words(line):
    return len([w for w in re.split(r"\s+", line.replace("…", " ").strip()) if re.search(r"[A-Za-z0-9]", w)])


def cap_for(script, cat):
    caps = script["caps"]
    if cat in ADVISOR_CATS:
        return caps["advisor"]
    return caps[cat]


def tag_for(spk, cat):
    tags = spk["tags"]
    if cat in ADVISOR_CATS:
        return tags.get("alert") if cat in ALERT_CATS and "alert" in tags else tags.get("advisor", "")
    group = TAG_GROUP.get(cat, cat)
    return tags.get(group) or tags.get(cat) or tags.get("other") or tags.get("ready", "")


def file_name(cat, n):
    return f"{cat}_{n:02d}"


def build_prompt(spk, cat, only=None, take_repeat=1):
    lines = spk["lines"][cat]
    idx = list(range(1, len(lines) + 1)) if not only else list(only)
    texts = [lines[i - 1] for i in idx]
    if take_repeat > 1:
        texts = texts * take_repeat
        idx = idx * take_repeat
    tag = tag_for(spk, cat)
    body = SEP.join(texts)
    prompt = (tag + " " + body) if tag else body
    return prompt, idx


def lint(script):
    bad = 0
    for sk, spk in script["speakers"].items():
        clans = spk["faction"] == "clans"
        for cat, lines in spk["lines"].items():
            wmax, smax = cap_for(script, cat)
            for i, ln in enumerate(lines, 1):
                w = words(ln)
                probs = []
                if w > wmax:
                    probs.append(f"{w} words > {wmax}")
                low = ln.lower()
                for b in BANNED_WORDS:
                    if re.search(r"(?<![a-z])" + re.escape(b) + r"(?![a-z])", low):
                        probs.append(f"banned word '{b}'")
                if re.search(r"\bfor the [a-z]+!", low):
                    probs.append("'For the X!' pattern")
                if cat == "ready" and low.startswith("ready to"):
                    probs.append("Ready line starts with 'Ready to'")
                if "hm-hm" in low and cat not in ("ready", "annoyed") and cat not in ADVISOR_CATS:
                    probs.append("'Hm-hm' outside Ready/Annoyed/advisor")
                if spk["faction"] == "kingdom" and (cat in ("built",) or cat in ADVISOR_CATS) and re.search(r"\bdone\b", low):
                    probs.append("'done' on a kingdom completion line")
                if re.search(r"\bme (?:hat|rifle|gun|hod|back)\b", low):
                    probs.append("dialect 'me' for 'my'")
                if clans and cat in ("what", "yes") and re.fullmatch(r"\W*h?m+[-\s]*h?m*\W*", low):
                    probs.append("bare interjection ack")
                if probs:
                    bad += 1
                    print(f"{sk}/{cat}_{i:02d}: {ln!r}: " + "; ".join(probs))
    print(f"lint: {bad} problem line(s)")
    return 1 if bad else 0


def cmd_cost(script, speakers=None, cats=None, quiet=False):
    total_chars = 0
    rows = []
    for sk, spk in script["speakers"].items():
        if speakers and sk not in speakers:
            continue
        for cat in CAT_ORDER:
            if cat not in spk["lines"] or (cats and cat not in cats):
                continue
            prompt, idx = build_prompt(spk, cat)
            mult = 2 if spk.get("voice_id_2") else 1
            n = len(prompt) * mult
            total_chars += n
            rows.append((sk, cat, len(idx), n, n * CU_PER_CHAR))
    if not quiet:
        for r in rows:
            print(f"{r[0]:14s} {r[1]:18s} lines {r[2]:2d}  chars {r[3]:4d}  {r[4]:6.2f} CU")
        print(f"TOTAL chars {total_chars}  {total_chars * CU_PER_CHAR:.2f} CU")
    return total_chars


def speaker_dirs(spk_key, spk):
    return os.path.join(OUT, spk["faction"], spk_key), os.path.join(RAW, spk["faction"], spk_key)


def find_job(jobs, job_id):
    for j in jobs:
        if j["job_id"].startswith(job_id):
            return j
    raise SystemExit(f"job {job_id} not in {JOBS}")


def post_params(spk):
    post = spk.get("post", "")
    tail = 0.3 if ("aecho" in post or "chorus" in post) else 0.0
    return post, tail


def process_job(script, job, keep=None, analyse=False, names=None, noise_db=-40.0):
    spk = script["speakers"][job["speaker"]]
    cat = job["category"]
    out_dir, raw_dir = speaker_dirs(job["speaker"], spk)
    raw = os.path.join(ROOT, job["raw"])
    idx = job["lines"]
    if names is None:
        names = [file_name(cat, n) for n in idx]
    post, tail = post_params(spk)
    max_s = cap_for(script, cat)[1]
    gap = MAX_GAP.get(cat, DEFAULT_GAP)
    rep = vo_split.run(raw, names, len(names), None if analyse else out_dir, max_s, post, tail, -18.0, noise_db, 0.35,
                       1.15, 5, analyse, set(keep) if keep else None, gap)
    rep_path = os.path.splitext(raw)[0] + ".report.json"
    if not analyse:
        with open(rep_path, "w") as f:
            json.dump(rep, f, indent=1)
            f.write("\n")
    return rep


def mix_unison(script, job_a, job_b, keep=None, offset_ms=14.0, noise_db=-40.0):
    """Sling-Cart: both brothers read the same lines; each line is mixed in unison (b delayed by offset_ms)."""
    spk = script["speakers"][job_a["speaker"]]
    cat = job_a["category"]
    assert job_a["lines"] == job_b["lines"], "both jobs must read the same lines"
    out_dir, _ = speaker_dirs(job_a["speaker"], spk)
    post, tail = post_params(spk)
    max_s = cap_for(script, cat)[1]
    segs = []
    for j in (job_a, job_b):
        x = vo_split.decode(os.path.join(ROOT, j["raw"]))
        an = vo_split.analyse(x, noise_db, 0.35, len(j["lines"]))
        if len(an["segments"]) != len(j["lines"]):
            raise SystemExit(f"{j['job_id']}: found {len(an['segments'])} lines, expected {len(j['lines'])}")
        gap = MAX_GAP.get(cat, DEFAULT_GAP)
        segs.append([vo_split.tighten(vo_split.trim(x[a * vo_split.HOP: b * vo_split.HOP], noise_db), noise_db, gap)
                     for a, b in an["segments"]])
    rows = []
    off = int(offset_ms / 1000 * vo_split.SR)
    for k, n in enumerate(job_a["lines"]):
        name = file_name(cat, n)
        if keep and n not in keep:
            continue
        a, b = segs[0][k], segs[1][k]
        # stretch the younger brother's take to the older one's length so the words land together (atempo 0.8-1.25)
        ratio = (len(b) + off) / max(1, len(a))
        if 0.8 <= ratio <= 1.25 and abs(ratio - 1) > 0.02:
            b = vo_split.ffmpeg_filter(b, f"atempo={ratio:.4f}")
        n_len = max(len(a), len(b) + off)
        m = np.zeros(n_len)
        m[: len(a)] += a * 0.6
        m[off: off + len(b)] += b * 0.6
        tempo = 1.0
        y, l = vo_split.process_line(m, post, tail, noise_db, tempo, -18.0, 1.15)
        dur = len(y) / vo_split.SR
        if dur > max_s and dur / max_s * 1.01 <= 1.15:
            tempo = dur / max_s * 1.01
            y, l = vo_split.process_line(m, post, tail, noise_db, tempo, -18.0, 1.15)
            dur = len(y) / vo_split.SR
        row = {"name": name, "a_s": round(len(segs[0][k]) / vo_split.SR, 3), "b_s": round(len(segs[1][k]) / vo_split.SR, 3),
               "tempo": round(tempo, 3), "final_s": round(dur, 3)}
        if dur > max_s:
            row["status"] = "REJECTED"
        else:
            path = os.path.join(out_dir, name + ".ogg")
            vo_split.export_ogg(y, path, 5)
            row["file"] = path
            row["status"] = "ok"
        rows.append(row)
    rep_path = os.path.splitext(os.path.join(ROOT, job_a["raw"]))[0] + ".unison.report.json"
    with open(rep_path, "w") as f:
        json.dump(rows, f, indent=1)
        f.write("\n")
    return rows


def cmd_manifest(script):
    man = {"_doc": "Generated by tools/audio/vo_tool.py manifest. One entry per voice; def_ids are every unit or hero def that uses it. "
                   "Category lists are ordered (annoyed plays in order; levelup_a may hold several takes of one line). "
                   "Lines and their status: docs/design/voice-lines.md.",
           "speakers": {}}
    for sk, spk in script["speakers"].items():
        out_dir, _ = speaker_dirs(sk, spk)
        cats = {}
        if os.path.isdir(out_dir):
            files = sorted(f for f in os.listdir(out_dir) if f.endswith(".ogg"))
            for cat in CAT_ORDER:
                got = [f for f in files if re.fullmatch(re.escape(cat) + r"_\d\d\.ogg", f)]
                if got:
                    cats[cat] = [f"res://assets/audio/voice/{spk['faction']}/{sk}/{f}" for f in got]
        entry = {"faction": spk["faction"], "role": spk["role"], "def_ids": spk["def_ids"], "voice_id": spk["voice_id"]}
        if spk.get("voice_id_2"):
            entry["voice_id_2"] = spk["voice_id_2"]
        entry["categories"] = cats
        man["speakers"][sk] = entry
    path = os.path.join(OUT, "manifest.json")
    os.makedirs(OUT, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=1, ensure_ascii=False)
        f.write("\n")
    n = sum(len(v) for s in man["speakers"].values() for v in s["categories"].values())
    print(f"manifest: {n} files -> {os.path.relpath(path, ROOT)}")


def cmd_spent(jobs):
    tot = sum(j.get("cost", 0) for j in jobs if j.get("charged", True))
    print(f"logged jobs: {len(jobs)}  charged: {tot:.4f} CU")
    return tot


def cmd_doc(script, jobs):
    from vo_doc import write_doc  # noqa: E402
    write_doc(script, jobs, DOC, OUT, ROOT, cap_for, words, file_name, CAT_ORDER, build_prompt, CU_PER_CHAR)
    print(f"wrote {os.path.relpath(DOC, ROOT)}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("lint")
    c = sub.add_parser("cost")
    c.add_argument("--speakers")
    c.add_argument("--cats")
    p = sub.add_parser("prompt")
    p.add_argument("speaker")
    p.add_argument("cat")
    p.add_argument("--only")
    p.add_argument("--repeat", type=int, default=1)
    p.add_argument("--voice-slot", type=int, default=1)
    lg = sub.add_parser("log")
    lg.add_argument("speaker")
    lg.add_argument("cat")
    lg.add_argument("job_id")
    lg.add_argument("--only")
    lg.add_argument("--repeat", type=int, default=1)
    lg.add_argument("--voice-slot", type=int, default=1)
    lg.add_argument("--status", default="submitted")
    lg.add_argument("--note", default="")
    lg.add_argument("--prompt-file", help="log this exact prompt (probe batches) instead of the built one")
    st = sub.add_parser("set")
    st.add_argument("job_id")
    st.add_argument("kv", nargs="+")
    pr = sub.add_parser("process")
    pr.add_argument("job_id")
    pr.add_argument("--keep")
    pr.add_argument("--analyse", action="store_true")
    pr.add_argument("--noise-db", type=float, default=-40.0)
    mu = sub.add_parser("mix-unison")
    mu.add_argument("job_a")
    mu.add_argument("job_b")
    mu.add_argument("--keep")
    sub.add_parser("manifest")
    sub.add_parser("doc")
    sub.add_parser("spent")
    a = ap.parse_args(argv)
    script = load_script()
    jobs = load_jobs()
    if a.cmd == "lint":
        return lint(script)
    if a.cmd == "cost":
        cmd_cost(script, a.speakers.split(",") if a.speakers else None, a.cats.split(",") if a.cats else None)
        return 0
    if a.cmd in ("prompt", "log"):
        spk = script["speakers"][a.speaker]
        only = [int(k) for k in a.only.split(",")] if a.only else None
        prompt, idx = build_prompt(spk, a.cat, only, a.repeat)
        if getattr(a, "prompt_file", None):
            with open(a.prompt_file, encoding="utf-8") as f:
                prompt = f.read()
        voice = spk["voice_id"] if a.voice_slot == 1 else spk["voice_id_2"]
        inp = {"model_id": MODEL_ID, "voice_id": voice, "prompt": prompt}
        if a.cmd == "prompt":
            print(json.dumps(inp, ensure_ascii=False))
            print(f"# chars {len(prompt)}  cost {len(prompt) * CU_PER_CHAR:.4f} CU  lines {idx}", file=sys.stderr)
            return 0
        if any(j["job_id"] == a.job_id for j in jobs):
            raise SystemExit("job already logged")
        _, raw_dir = speaker_dirs(a.speaker, spk)
        suffix = "" if a.voice_slot == 1 else f"_v{a.voice_slot}"
        raw_rel = os.path.relpath(os.path.join(raw_dir, f"{a.cat}{suffix}_{a.job_id[:8]}.mp3"), ROOT)
        jobs.append({"date": "2026-10-20", "job_id": a.job_id, "speaker": a.speaker, "category": a.cat, "lines": idx,
                     "voice_id": voice, "model_id": MODEL_ID, "prompt": prompt, "chars": len(prompt),
                     "cost": round(len(prompt) * CU_PER_CHAR, 4), "status": a.status, "raw": raw_rel, "note": a.note})
        save_jobs(jobs)
        print(json.dumps(jobs[-1], ensure_ascii=False))
        return 0
    if a.cmd == "set":
        j = find_job(jobs, a.job_id)
        for kv in a.kv:
            k, v = kv.split("=", 1)
            if v in ("true", "false"):
                v = v == "true"
            else:
                try:
                    v = float(v) if "." in v else int(v)
                except ValueError:
                    pass
            j[k] = v
        save_jobs(jobs)
        print(json.dumps(j, ensure_ascii=False))
        return 0
    if a.cmd == "process":
        j = find_job(jobs, a.job_id)
        keep = [int(k) for k in a.keep.split(",")] if a.keep else None
        rep = process_job(script, j, keep, a.analyse, noise_db=a.noise_db)
        print(json.dumps(rep, indent=1))
        return 0 if rep["found"] == len(j["lines"]) else 2
    if a.cmd == "mix-unison":
        ja, jb = find_job(jobs, a.job_a), find_job(jobs, a.job_b)
        keep = [int(k) for k in a.keep.split(",")] if a.keep else None
        print(json.dumps(mix_unison(script, ja, jb, keep), indent=1))
        return 0
    if a.cmd == "manifest":
        cmd_manifest(script)
        return 0
    if a.cmd == "doc":
        cmd_doc(script, jobs)
        return 0
    if a.cmd == "spent":
        cmd_spent(jobs)
        return 0


if __name__ == "__main__":
    sys.exit(main())
