export const meta = {
  name: 'audio-p0-pass',
  description: 'First audio pass on a capped Krea budget: unit/hero voice acks, P0 combat+order SFX, first music pieces; QA, ledger, manifest',
  phases: [
    { title: 'Generate', detail: 'voice and SFX+music agents in parallel, separate worktree' },
    { title: 'QA', detail: 'audio QA, ledger merge, manifest, commit' },
  ],
}

const R = '/home/user/Vibecraft'
const WT = '/tmp/vc_audio'
const AB = 'audio/p0'
const ENV = `
PROJECT: Vibecraft, a Godot 4.7.2 3D RTS that plays as close to Warcraft III as legally possible with 100% ORIGINAL names, art, text and audio. Repo ${R}. You work in the git worktree ${WT} on local branch ${AB} (create it ONCE with: git -C ${R} worktree add ${WT} -b ${AB} claude/clever-heisenberg-i8649y ; RESUME RULE: if ${WT} or branch ${AB} already exists, an earlier run was interrupted: do NOT recreate it, cd in, read git log and the files, and CONTINUE). Other agents are working in ${R} itself: never edit, stage or commit anything in ${R}; only in ${WT}.
READ (grep/section reads, the files are long): ${WT}/docs/design/art-and-audio-bible.md §8 Voice (8.1 rules, 8.2 categories/counts/budgets, 8.3-8.5 speakers and post-chains, 8.6-8.10 lines, 8.11 TTS recipe), §9 SFX (9.1 wrappers and post, 9.2-9.8 tables, 9.9 job count), §10 Music, §11 budget; ${WT}/docs/design/juice/ui-camera-audio.md (AUD-* rows: ids, buses, debounce), ${WT}/docs/design/juice/combat-and-units.md (CMB-* sound ids), ${WT}/docs/research/ip-safety.md §2.2 and §2.5, ${WT}/docs/asset-ledger.md (cost history), ${WT}/data/units.json and ${WT}/data/heroes.json (def ids), ${WT}/docs/architecture.md §12 Audio.
PAID GENERATION (this is the ONLY workflow allowed to spend):
- Krea MCP tools: mcp__Krea_MCP__generate_audio (models elevenlabs/tts, bytedance/seed-audio-1.0, elevenlabs/music-v2.5), mcp__Krea_MCP__get_job, mcp__Krea_MCP__get_balance. If these tools are not available to you (load them with ToolSearch "select:mcp__Krea_MCP__generate_audio,mcp__Krea_MCP__get_job,mcp__Krea_MCP__get_balance"), STOP immediately and say so in your final reply. Do NOT use Higgsfield (its credits are reserved for 3D).
- ALWAYS submit async (sync false), write the job id to your ledger file IMMEDIATELY, then poll get_job until completed and download the result URL with curl (outbound HTTPS goes through the preconfigured proxy; never disable TLS verification). A 429 (too many concurrent jobs) is not charged: wait 20-60 s and retry. Another agent may be submitting at the same time; keep at most 2 of your own jobs in flight.
- Measured prices (2026-10-20 preflights): elevenlabs/tts bills PER CHARACTER of the prompt, about 0.075 CU per character (1.63 CU for 21 chars, 8 CU for 108 chars), bracket tags included, so keep tags short; seed-audio 4.63 CU for a 2.5 s clip (whether it scales with length is UNMEASURED); music unmeasured. Use preflight:true (free) to quote before every new kind of request, and get_balance before and after your first job of each kind to learn the real charge.
- HARD BUDGET CAP for your agent is stated in your task. Track spend with get_balance; never exceed it. Leave the rest of the Krea balance alone: it funds icons and UI art later.
- Ledger: append one row per job (date 2026-10-20, service, what, job id, cost, result, including rejected takes and failed jobs) to YOUR OWN file ${WT}/docs/ledger-pending/<your-agent-name>.md (table columns: | Service | What | Job id | Cost | Result |). The QA agent merges these into docs/asset-ledger.md.
IP AND CONTENT RULES: never use a franchise, game, studio, film, composer, performer or person's name in any prompt; never a line or paraphrase from the reference game (bible §8.1 rule 3 lists the traps: no "poke", no "For the X!" warcry, no stock military acks, no broken-English worker grammar, no elected-king jokes, no "done" on kingdom completions, no address-word swaps of reference lines, no wind-speaker gags); preset ElevenLabs voices only, no cloning. Run python3 tools/ip/check_banned_terms.py in ${WT} before every commit (must print "no banned terms").
TOOLS: ffmpeg/ffprobe (with loudnorm, silencedetect, atempo, rubberband, asetrate) are installed; python3 with numpy. Write helper scripts under ${WT}/tools/audio/ (they become part of the repo: make them reusable, e.g. tools/audio/split_takes.py that splits on silence, trims, fades, normalises and exports, with a --help). Raw downloads go to ${WT}/assets_src/audio/... (assets_src has a .gdignore). Final game files go under ${WT}/assets/audio/...
GIT: commit EARLY AND OFTEN in ${WT} on ${AB} with clear messages (after each speaker / each SFX group). Never push. Never rewrite history. A usage limit can kill you at any time: frequent commits let a restarted agent continue (and the ledger file prevents paying twice: before submitting any job, check your ledger file and the assets for work already done).
FINAL REPLY: what was generated (counts per speaker/group), total CU spent (from get_balance), files/paths, rejected takes, anything not done and why.
`

phase('Generate')
const [vo, sfx] = await parallel([
  () => agent(`${ENV}
YOUR NAME: audio-vo. HARD BUDGET CAP: 300 CU total for everything you submit.
TASK: voice the slice units and heroes so that selecting and ordering units in the playtest has character (this is the single biggest piece of classic-RTS feel still missing).
1. Speakers: the slice units and heroes in data/units.json and data/heroes.json for both factions (kingdom: hodman (the Flail Levy shares the hodman voice), pavisier, hookgunner, linden_sister, bombard_wagon crew, heroes wheel_marshal and firewright; clans: yurtwright, grappler, javelineer, gustcaller, sling_cart crew, heroes uncut and skymirror). Casting, tics and post-chains come from bible §8.3-§8.4; if a speaker has no voice id or tic there, pick one consistent with the faction rules and write it down.
2. Lines: bible §8.6-§8.9 have finished lines for the hodman, pavisier, yurtwright and grappler. For every other speaker WRITE original lines that obey §8.1 (word and second budgets, faction vocabulary, one tic per speaker, character comedy only, all the IP traps) and §8.2 category counts. Put ALL lines (existing and new) in ${WT}/docs/design/voice-lines.md (speaker, category, number, text, voice id, file path) so later passes and reviewers can see them. Re-read every new line against the §8.1 trap list before generating.
3. Priority order within the 300 CU cap (compute the character cost of each batch first and stop a tier when the cap would be crossed):
   a) every speaker: ready, what, yes, attack (warcry for heroes), plus hero level-up if the bible has that category;
   b) annoyed sequences for the hodman, yurtwright, pavisier and grappler;
   c) the two advisors' P0 alert lines (under attack, not enough gold/lumber, supply blocked, building complete, research complete) from §8.10;
   d) anything else P0 in §8.2 as budget allows.
4. Generation: follow §8.11 exactly (eleven_v4, batch one category of one speaker per request, short bracket tags). Before the batch run, do ONE probe batch (one speaker's What lines) and listen-check by measurement: split it, check each take's duration against §8.2, check loudness, and check the text maps to the right takes. If takes merge or split wrongly, adjust the "[long pause]" separators before scaling up.
5. Post: split on silence, trim, the speaker's post-chain, 5 ms/20 ms fades, about -18 LUFS, duration checks with atempo ≤1.15 and rejection over the category cap (a What or Yes over 1.4 s never ships). Export Ogg Vorbis mono -q:a 5 to assets/audio/voice/<faction>/<speaker>/<category>_<nn>.ogg (bible §8.11 path). Raw takes to assets_src/audio/voice/.
6. Write ${WT}/assets/audio/voice/manifest.json: {"speakers": {"<speaker>": {"faction":..., "def_ids": [every unit/hero def id that uses this voice], "voice_id":..., "categories": {"what": ["res://assets/audio/voice/kingdom/hodman/what_01.ogg", ...], ...}}}}.
Commit after each speaker.`, { label: 'audio:vo', phase: 'Generate' }),
  () => agent(`${ENV}
YOUR NAME: audio-sfx. HARD BUDGET CAP: 170 CU for SFX plus 130 CU for music (300 CU total).
TASK A, SFX for the first playtest (a battlefield sandbox: select units, move, attack-move, melee and ranged fights, deaths, a few hero abilities):
1. FIRST a probe (bible §11 decision 1): one 4-variant Seed Audio job with the SFX_ONESHOT_V1 wrapper for a P0 combat sound; record the charge with get_balance before/after. If Seed Audio bills per job (about 4.6 CU regardless of length), use kit sets (wrapper K) and multi-variant jobs aggressively. If it bills per second, keep variants short and the silences at 0.6 s.
2. Generate, in this order, as the cap allows: the P0 combat matrix (§9.3: weapon swings and impacts by material, sw_pierce, body falls, deaths/"fall" cues, hit_sub), the P0 ranged/siege set (§9.4: hookgun shot, javelin throw and impact, sling, bombard shot and impact, arrows), the P0 order/selection/UI kit sets of §9.2 (move and attack acknowledgement ticks, selection, deny/error, button click), then the hero-ability P0 cues for the four slice heroes from §9.6 if budget remains. Follow the §9.1 wrappers and clause tables exactly; ids and file names from the bible tables.
3. CC0 fallback (bible §11 decision 2): the most generic sounds (body falls, coin and lumber drops, UI clicks/ticks) may instead come from Kenney's CC0 packs (kenney.nl "Impact Sounds", "RPG Audio", "Interface Sounds") if you can download them through the proxy; keep their CC0 licence text, add assets/audio/CREDITS.md entries, and never use stock sounds for the signature cues the bible lists. If downloads fail, generate instead.
4. Post per §9.1: split on silence, discard bad takes (clipped, wrong content, too long, speech or music present: check with ffprobe/numpy measurements such as duration, peak, spectral centroid and silence ratio, and reject outliers), trim, fades, peak -1 dBFS, WAV 44.1 kHz mono, names assets/audio/sfx/<group>/<id>_<nn>.wav. Raw to assets_src/audio/sfx/.
TASK B, music (bible §10, ElevenLabs Music v2.5 through Krea, force_instrumental true, explicit music_length_ms):
1. Probe: generate the kingdom match-opening cue (10 s) first and record the charge; derive the per-second price.
2. Then, within the 130 CU music cap: Kingdom 1 "Market-Day Muster" and Clans 1 "Herd Road" (full length if affordable, otherwise shorten music_length_ms to fit and note it), then the clans opening cue, then the menu theme if anything remains. Use the §10.3 prompts verbatim; never add names. Post per §10.4 (trim tail, about -16 LUFS, Ogg Vorbis stereo -q:a 6, assets/audio/music/<name>.ogg; opening cues trimmed to 2.4 s with a 300 ms fade).
Write ${WT}/assets/audio/sfx/manifest.json ({"<id>": ["res://...wav", ...]}) and ${WT}/assets/audio/music/manifest.json (piece -> file, length, prompt id). Commit after each group.`, { label: 'audio:sfx+music', phase: 'Generate' }),
])
if (!vo || !sfx) throw new Error('Generation incomplete - resume later')

phase('QA')
const qa = await agent(`${ENV}
YOUR NAME: audio-qa. You spend NOTHING (no generation calls).
TASK: quality and integration check of the audio generated on ${AB} in ${WT}.
Voice summary:\n${vo}\n\nSFX/music summary:\n${sfx}\n
1. Check every file under assets/audio: decodes with ffprobe, correct format (voice Ogg mono, SFX WAV 44.1 kHz mono, music Ogg stereo), no clipping (peak ≤ -0.9 dBFS), loudness within ±2 LU of target, durations within bible caps (What/Yes ≤ 1.4 s), no leading/trailing silence over 60 ms on one-shots, no duplicate takes (compare fingerprints, e.g. downsampled RMS envelopes). Fix with the tools/audio scripts or delete bad takes (and update manifests). Report what you removed.
2. Every manifest entry exists and every file is in a manifest. The voice manifest maps every slice unit/hero def id in data/units.json and data/heroes.json to a speaker.
3. Run "godot --headless --path ${WT} --import" (run it once; first time can take minutes) and make sure all audio imports with no errors (set loop flags in the .import files for loops/beds: SFX_LOOP ids and ambience; music does not loop except menu/score). Commit the .import files.
4. Merge every docs/ledger-pending/*.md into docs/asset-ledger.md as numbered spend-log rows continuing the existing numbering (the last row is 24; check), add measured unit costs to the "Measured unit costs" table (TTS per character, Seed Audio per job or per second, music per second), update the "Balances after log" line with get_balance (read-only) — mcp__Krea_MCP__get_balance is allowed for you — then delete docs/ledger-pending/.
5. Update docs/architecture.md §12 Audio with the real file layout and the three manifests (assets/audio/voice/manifest.json, sfx/manifest.json, music/manifest.json) so the Audio autoload can load by manifest; keep tools/README.md updated with the tools/audio scripts.
6. python3 tools/ip/check_banned_terms.py must pass. Commit on ${AB}. Do not merge into the main branch (the orchestrator does that).
FINAL REPLY: per-folder counts, removed files, loudness/duration stats, total CU spent this pass, remaining Krea balance, anything the Audio autoload must do to use the manifests.`, { label: 'audio:qa', phase: 'QA' })
if (!qa) throw new Error('QA incomplete - resume later')
return { vo, sfx, qa }
