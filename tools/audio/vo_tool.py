#!/usr/bin/env python3
"""Voice-over pipeline for the slice: script lint, TTS prompts and costs, job log, post-processing, manifest, docs.

Source of record: tools/prompts/vo/vo_script.json (every line, voice id, tag set and post-chain per speaker).
Plan:             tools/prompts/vo/vo_plan.json (requests in priority order, tiers a-d).
Job log:          tools/prompts/vo/vo_jobs.json (every paid request: prompt, characters, cost, job id, result).
Raw downloads:    assets_src/audio/voice/<faction>/<speaker>/<batch>_<job8>.mp3 (+ .report.json from the split).
Game files:       assets/audio/voice/<faction>/<speaker>/<category>_<nn>.ogg and assets/audio/voice/manifest.json.

A request ("batch") is one speaker and a list of items "category:n" (1-based line numbers in the script), normally
one category (art bible 8.11); the two level-up categories form one batch, and an advisor's alerts form one batch.

Pricing (Krea elevenlabs/tts, measured 2026-10-20 with free preflights): 2/27 CU per prompt character, everything
counted (tags, spaces, newlines). Every quote below is exact.

Subcommands:
  lint                                   word budgets, banned words, faction rules (exit 1 on a violation)
  cost  [--speakers a,b] [--cats x,y]    full-script characters and CU per category batch
  plan  [--tier a]                       remaining planned batches (items not yet exported or in flight) and CU
  prompt SPEAKER ITEMS [--slot 2]        print the request input JSON; ITEMS like "what:1,what:3" or "what" (all)
  log   SPEAKER ITEMS JOB_ID [--slot 2] [--tier a] [--note ..]   append a submitted job to the job log
  set   JOB_ID key=value ...             update a job (status, url, charged, note)
  process JOB_ID [--keep 1,2] [--analyse] [--noise-db -40]       split + post + export one downloaded job
  mix-unison JOB_A JOB_B [--keep ..]     (Sling-Cart) split both brothers' takes and mix each line in unison
  manifest                               write assets/audio/voice/manifest.json from the files on disk
  doc                                    write docs/design/voice-lines.md from the script, the job log and the files
  spent                                  total CU of all logged jobs
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
PLAN = os.path.join(ROOT, "tools/prompts/vo/vo_plan.json")
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
# Pauses inside a line are tightened to at most this many seconds (vo_split --max-gap). Acks must land in 1.4 s.
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
                "warchief", "sabre", "saber", "spirits", "omen"]


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_jobs(jobs):
    with open(JOBS, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=1, ensure_ascii=False)
        f.write("\n")


def words(line):
    return len([w for w in re.split(r"\s+", line.replace("…", " ").strip()) if re.search(r"[A-Za-z0-9]", w)])


def cap_for(script, cat):
    caps = script["caps"]
    return caps["advisor"] if cat in ADVISOR_CATS else caps[cat]


def tag_for(spk, cat):
    tags = spk["tags"]
    if cat in ADVISOR_CATS:
        return tags.get("alert") if cat in ALERT_CATS and "alert" in tags else tags.get("advisor", "")
    group = TAG_GROUP.get(cat, cat)
    return tags.get(group) or tags.get(cat) or tags.get("other") or tags.get("ready", "")


def file_name(cat, n):
    return f"{cat}_{n:02d}"


def parse_items(spk, spec):
    """'what:1,what:3' -> [('what',1),('what',3)]; 'what' -> every line of that category."""
    items = []
    for part in spec.split(","):
        if ":" in part:
            c, n = part.split(":")
            items.append((c, int(n)))
        else:
            items += [(part, n) for n in range(1, len(spk["lines"][part]) + 1)]
    return items


def build_prompt(spk, items):
    texts = [spk["lines"][c][n - 1] for c, n in items]
    tag = tag_for(spk, items[0][0])
    body = SEP.join(texts)
    return (tag + " " + body) if tag else body


def batch_label(items):
    cats = []
    for c, _ in items:
        if c not in cats:
            cats.append(c)
    if len(cats) == 1:
        return cats[0]
    if all(c in ADVISOR_CATS for c in cats):
        return "advisor"
    if all(c.startswith("levelup") for c in cats):
        return "levelup"
    return "+".join(cats)


def job_items(j):
    if "items" in j:
        return [tuple(x) for x in j["items"]]
    return [(j["category"], n) for n in j["lines"]]


def lint(script):
    bad = 0
    for sk, spk in script["speakers"].items():
        clans = spk["faction"] == "clans"
        for cat, lines in spk["lines"].items():
            wmax, _ = cap_for(script, cat)
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
                if spk["faction"] == "kingdom" and (cat == "built" or cat in ADVISOR_CATS) and re.search(r"\bdone\b", low):
                    probs.append("'done' on a kingdom completion line")
                if re.search(r"\bme (?:hat|rifle|gun|hod|back|card)\b", low):
                    probs.append("dialect 'me' for 'my'")
                if clans and cat in ("what", "yes") and re.fullmatch(r"\W*h?m+[-\s]*h?m*\W*", low):
                    probs.append("bare interjection ack")
                if probs:
                    bad += 1
                    print(f"{sk}/{cat}_{i:02d}: {ln!r}: " + "; ".join(probs))
    print(f"lint: {bad} problem line(s)")
    return 1 if bad else 0


def batch_chars(spk, items):
    return len(build_prompt(spk, items)) * (2 if spk.get("voice_id_2") else 1)


def cmd_cost(script, speakers=None, cats=None):
    total = 0
    for sk, spk in script["speakers"].items():
        if speakers and sk not in speakers:
            continue
        for cat in CAT_ORDER:
            if cat not in spk["lines"] or (cats and cat not in cats):
                continue
            items = [(cat, n) for n in range(1, len(spk["lines"][cat]) + 1)]
            n = batch_chars(spk, items)
            total += n
            print(f"{sk:14s} {cat:18s} lines {len(items):2d}  chars {n:4d}  {n * CU_PER_CHAR:6.2f} CU")
    print(f"TOTAL chars {total}  {total * CU_PER_CHAR:.2f} CU")


def exported(spk_key, spk, cat, n):
    return os.path.exists(os.path.join(OUT, spk["faction"], spk_key, file_name(cat, n) + ".ogg"))


def in_flight(jobs, spk_key, cat, n):
    return any(j["speaker"] == spk_key and (cat, n) in job_items(j) and j.get("status") in ("submitted", "completed")
               and not j.get("superseded") for j in jobs)


def remaining_plan(script, jobs, tier=None):
    plan = load_json(PLAN, {"tiers": {}})
    out = []
    for t, batches in plan["tiers"].items():
        if tier and t != tier:
            continue
        for b in batches:
            sk, items = b[0], [tuple(x) for x in b[1]]
            spk = script["speakers"][sk]
            todo = [(c, n) for c, n in items if not exported(sk, spk, c, n) and not in_flight(jobs, sk, c, n)]
            if todo:
                out.append((t, sk, todo, batch_chars(spk, todo)))
    return out


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


def process_job(script, job, keep=None, analyse=False, noise_db=-40.0):
    spk = script["speakers"][job["speaker"]]
    items = job_items(job)
    out_dir, _ = speaker_dirs(job["speaker"], spk)
    raw = os.path.join(ROOT, job["raw"])
    names = [file_name(c, n) for c, n in items]
    post, tail = post_params(spk)
    max_s = [cap_for(script, c)[1] for c, _ in items]
    gaps = [MAX_GAP.get(c, DEFAULT_GAP) for c, _ in items]
    rep = vo_split.run(raw, names, len(names), None if analyse else out_dir, max_s, post, tail, -18.0, noise_db, 0.35,
                       1.15, 5, analyse, set(keep) if keep else None, gaps)
    if not analyse:
        with open(os.path.splitext(raw)[0] + ".report.json", "w") as f:
            json.dump(rep, f, indent=1)
            f.write("\n")
    return rep


def mix_unison(script, job_a, job_b, keep=None, offset_ms=14.0, noise_db=-40.0):
    """Sling-Cart: both brothers read the same lines; each line is mixed in unison (b delayed by offset_ms)."""
    spk = script["speakers"][job_a["speaker"]]
    items = job_items(job_a)
    assert items == job_items(job_b), "both jobs must read the same lines"
    out_dir, _ = speaker_dirs(job_a["speaker"], spk)
    post, tail = post_params(spk)
    segs = []
    for j in (job_a, job_b):
        x = vo_split.decode(os.path.join(ROOT, j["raw"]))
        an = vo_split.analyse(x, noise_db, 0.35, len(items))
        if len(an["segments"]) != len(items):
            raise SystemExit(f"{j['job_id']}: found {len(an['segments'])} lines, expected {len(items)}")
        segs.append([vo_split.tighten(vo_split.trim(x[a * vo_split.HOP: b * vo_split.HOP], noise_db), noise_db,
                                      MAX_GAP.get(items[k][0], DEFAULT_GAP))
                     for k, (a, b) in enumerate(an["segments"])])
    rows = []
    off = int(offset_ms / 1000 * vo_split.SR)
    for k, (cat, n) in enumerate(items):
        if keep and (k + 1) not in keep:
            continue
        max_s = cap_for(script, cat)[1]
        name = file_name(cat, n)
        a, b = segs[0][k], segs[1][k]
        # fit the younger brother's take to the older one's length so the words land together (atempo 0.8-1.25)
        ratio = len(b) / max(1, len(a))
        if 0.8 <= ratio <= 1.25 and abs(ratio - 1) > 0.02:
            b = vo_split.ffmpeg_filter(b, f"atempo={ratio:.4f}")
        m = np.zeros(max(len(a), len(b) + off))
        m[: len(a)] += a * 0.6
        m[off: off + len(b)] += b * 0.6
        tempo = 1.0
        y, l = vo_split.process_line(m, post, tail, noise_db, tempo, -18.0, 1.15)
        dur = len(y) / vo_split.SR
        for _ in range(4):
            if dur <= max_s or tempo >= 1.15:
                break
            tempo = min(1.15, tempo * dur / max_s * 1.015)
            y, l = vo_split.process_line(m, post, tail, noise_db, tempo, -18.0, 1.15)
            dur = len(y) / vo_split.SR
        row = {"name": name, "older_s": round(len(a) / vo_split.SR, 3), "younger_s": round(len(segs[1][k]) / vo_split.SR, 3),
               "tempo": round(tempo, 3), "final_s": round(dur, 3)}
        if dur > max_s:
            row["status"] = f"REJECTED (over {max_s} s)"
        else:
            path = os.path.join(out_dir, name + ".ogg")
            vo_split.export_ogg(y, path, 5)
            row.update({"file": os.path.relpath(path, ROOT), "status": "ok"})
        rows.append(row)
    with open(os.path.splitext(os.path.join(ROOT, job_a["raw"]))[0] + ".unison.report.json", "w") as f:
        json.dump(rows, f, indent=1)
        f.write("\n")
    return rows


def cmd_manifest(script):
    man = {"_doc": "Generated by tools/audio/vo_tool.py manifest. One entry per voice; def_ids are every unit or hero def that "
                   "uses it (advisors have none: they speak for the faction). Category lists are ordered: annoyed plays "
                   "in order, the last line is the punchline. Lines, status and files: docs/design/voice-lines.md.",
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


LEDGER = os.path.join(ROOT, "docs/ledger-pending/audio-vo.md")


def ledger_upsert(job, result):
    """One row per job in the agent's pending ledger (| Service | What | Job id | Cost | Result |); rewrites the row's result."""
    what = f"{job.get('tier') and 'tier ' + job['tier'] + ': ' or ''}{job['speaker']} {job['category']} " \
           f"({', '.join(f'{c}_{n:02d}' for c, n in job_items(job))}; voice {job['voice_id']}; {job['chars']} chars)"
    if job.get("note"):
        what += f"; {job['note']}"
    row = f"| ElevenLabs TTS via Krea (elevenlabs/tts, eleven_v4) | {what} | {job['job_id']} | {job['cost']:.2f} CU | {result} |"
    lines = open(LEDGER, encoding="utf-8").read().splitlines() if os.path.exists(LEDGER) else []
    for i, ln in enumerate(lines):
        if f"| {job['job_id']} |" in ln:
            lines[i] = row
            break
    else:
        lines.append(row)
    with open(LEDGER, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def summarize(rep):
    out = []
    for r in rep["lines"]:
        st = r.get("status", "")
        out.append(f"{r.get('name')}: {st.split(' ')[0]} {r.get('final_s', '')}s"
                   + (f" atempo {r['tempo']}" if r.get("tempo", 1) != 1 else ""))
    return "; ".join(out)


def spent(jobs):
    return sum(j.get("cost", 0) for j in jobs if j.get("charged", True))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("lint")
    c = sub.add_parser("cost")
    c.add_argument("--speakers")
    c.add_argument("--cats")
    pl = sub.add_parser("plan")
    pl.add_argument("--tier")
    for name in ("prompt", "log"):
        p = sub.add_parser(name)
        p.add_argument("speaker")
        p.add_argument("items")
        if name == "log":
            p.add_argument("job_id")
            p.add_argument("--tier", default="")
            p.add_argument("--note", default="")
            p.add_argument("--prompt-file", help="log this exact prompt (probe batches) instead of the built one")
        p.add_argument("--slot", type=int, default=1, help="2 = the second voice (Sling-Cart younger brother)")
    st = sub.add_parser("set")
    st.add_argument("job_id")
    st.add_argument("kv", nargs="+")
    pr = sub.add_parser("process")
    pr.add_argument("job_id")
    pr.add_argument("--keep")
    pr.add_argument("--analyse", action="store_true")
    pr.add_argument("--noise-db", type=float, default=-40.0)
    fe = sub.add_parser("fetch", help="download a completed job's result URL, then process it")
    fe.add_argument("job_id")
    fe.add_argument("url")
    fe.add_argument("--no-process", action="store_true")
    mu = sub.add_parser("mix-unison")
    mu.add_argument("job_a")
    mu.add_argument("job_b")
    mu.add_argument("--keep")
    sub.add_parser("manifest")
    sub.add_parser("doc")
    sub.add_parser("spent")
    a = ap.parse_args(argv)
    script = load_json(SCRIPT)
    jobs = load_json(JOBS, [])
    if a.cmd == "lint":
        return lint(script)
    if a.cmd == "cost":
        cmd_cost(script, a.speakers.split(",") if a.speakers else None, a.cats.split(",") if a.cats else None)
        return 0
    if a.cmd == "plan":
        rows = remaining_plan(script, jobs, a.tier)
        tot = 0
        for t, sk, todo, n in rows:
            tot += n
            print(f"{t} {sk:14s} {','.join(f'{c}:{i}' for c, i in todo):60s} chars {n:4d} {n * CU_PER_CHAR:6.2f} CU  cum {tot * CU_PER_CHAR:7.2f}")
        print(f"remaining planned: {len(rows)} batches, {tot} chars, {tot * CU_PER_CHAR:.2f} CU; spent so far {spent(jobs):.2f} CU")
        return 0
    if a.cmd in ("prompt", "log"):
        spk = script["speakers"][a.speaker]
        items = parse_items(spk, a.items)
        prompt = build_prompt(spk, items)
        if getattr(a, "prompt_file", None):
            with open(a.prompt_file, encoding="utf-8") as f:
                prompt = f.read()
        voice = spk["voice_id"] if a.slot == 1 else spk["voice_id_2"]
        inp = {"model_id": MODEL_ID, "voice_id": voice, "prompt": prompt}
        if a.cmd == "prompt":
            print(json.dumps(inp, ensure_ascii=False))
            print(f"# chars {len(prompt)}  cost {len(prompt) * CU_PER_CHAR:.4f} CU  items {items}", file=sys.stderr)
            return 0
        if any(j["job_id"] == a.job_id for j in jobs):
            raise SystemExit("job already logged")
        _, raw_dir = speaker_dirs(a.speaker, spk)
        suffix = "" if a.slot == 1 else f"_v{a.slot}"
        raw_rel = os.path.relpath(os.path.join(raw_dir, f"{batch_label(items)}{suffix}_{a.job_id[:8]}.mp3"), ROOT)
        jobs.append({"date": "2026-10-20", "job_id": a.job_id, "tier": a.tier, "speaker": a.speaker,
                     "category": batch_label(items), "items": [list(x) for x in items], "voice_id": voice,
                     "model_id": MODEL_ID, "prompt": prompt, "chars": len(prompt),
                     "cost": round(len(prompt) * CU_PER_CHAR, 4), "status": "submitted", "raw": raw_rel, "note": a.note})
        save_jobs(jobs)
        ledger_upsert(jobs[-1], "submitted")
        print(f"logged {a.job_id} {a.speaker} {batch_label(items)} {len(prompt)} chars {len(prompt) * CU_PER_CHAR:.4f} CU -> {raw_rel}")
        return 0
    if a.cmd == "set":
        j = find_job(jobs, a.job_id)
        for kv in a.kv:
            k, v = kv.split("=", 1)
            if v in ("true", "false"):
                v = v == "true"
            j[k] = v
        save_jobs(jobs)
        return 0
    if a.cmd == "process":
        j = find_job(jobs, a.job_id)
        keep = [int(k) for k in a.keep.split(",")] if a.keep else None
        rep = process_job(script, j, keep, a.analyse, noise_db=a.noise_db)
        print(json.dumps(rep, indent=1))
        return 0 if rep["found"] == len(job_items(j)) else 2
    if a.cmd == "fetch":
        import subprocess
        j = find_job(jobs, a.job_id)
        raw = os.path.join(ROOT, j["raw"])
        os.makedirs(os.path.dirname(raw), exist_ok=True)
        subprocess.run(["curl", "-sS", "--fail", "--retry", "3", "-o", raw, a.url], check=True)
        j["status"] = "completed"
        j["url"] = a.url
        save_jobs(jobs)
        if a.no_process:
            ledger_upsert(j, "completed, raw downloaded")
            print(f"downloaded {j['raw']}")
            return 0
        rep = process_job(script, j)
        summ = summarize(rep)
        if rep["found"] != len(job_items(j)):
            summ = f"SPLIT MISMATCH: found {rep['found']} of {len(job_items(j))}"
        j["result"] = summ
        save_jobs(jobs)
        ledger_upsert(j, summ)
        print(summ)
        return 0 if rep["found"] == len(job_items(j)) else 2
    if a.cmd == "mix-unison":
        ja, jb = find_job(jobs, a.job_a), find_job(jobs, a.job_b)
        keep = [int(k) for k in a.keep.split(",")] if a.keep else None
        print(json.dumps(mix_unison(script, ja, jb, keep), indent=1))
        return 0
    if a.cmd == "manifest":
        cmd_manifest(script)
        return 0
    if a.cmd == "doc":
        import vo_doc
        vo_doc.write_doc(script, jobs)
        print(f"wrote {os.path.relpath(DOC, ROOT)}")
        return 0
    if a.cmd == "spent":
        print(f"logged jobs: {len(jobs)}  charged: {spent(jobs):.4f} CU")
        return 0


if __name__ == "__main__":
    sys.exit(main())
