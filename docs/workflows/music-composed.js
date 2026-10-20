export const meta = {
  name: 'music-composed',
  description: 'Compose and render all remaining game music ourselves (no paid APIs): toolkit, per-faction composers, critic + revise loop, integration',
  phases: [
    { title: 'Toolkit', detail: 'composition + rendering toolkit, sound palette, style tests' },
    { title: 'Compose', detail: 'kingdom, clans and shared pieces' },
    { title: 'Review', detail: 'critic per group' },
    { title: 'Revise', detail: 'fix critic findings' },
    { title: 'Integrate', detail: 'manifest, credits, docs, session hook, final checks' },
  ],
}

const R = '/home/user/Vibecraft'
const WT = '/tmp/vc_music'
const MB = 'music/p0'
const ENV = `
PROJECT: Vibecraft, a Godot 4.7.2 3D RTS that plays as close to Warcraft III as legally possible with 100% ORIGINAL names, art, text and audio. Repo ${R}. The user asked us to COMPOSE THE MUSIC OURSELVES instead of paying for AI music (Krea's music model cost 444 CU for 10 s; it is banned). NO paid API calls of any kind (no Krea, no Higgsfield).
WHERE YOU WORK: git worktree ${WT} on local branch ${MB}. If ${WT} does not exist yet, create it with: git -C ${R} worktree add ${WT} -b ${MB} claude/clever-heisenberg-i8649y . RESUME RULE: if it already exists (an earlier run was interrupted), do not recreate it: cd in, read git log and the files, and CONTINUE. Other agents (the Playtest 1 build) work in ${R} itself: never edit, stage or commit anything in ${R}. Other music agents may work in ${WT} at the same time on OTHER pieces: only stage and commit your own paths (git add -- <paths>; git commit -m ... -- <paths>), retry after a few seconds if .git/index.lock exists, never "git add -A", never revert someone else's files.
READ: ${WT}/docs/design/art-and-audio-bible.md §10 Music (10.1 plan, lengths and rules incl. the AVOID list, 10.2 our motifs, 10.3 per-piece briefs: use them as the musical brief for key, mode, tempo, instruments, mood and structure, 10.4 post-processing and file names), the faction docs ${WT}/docs/design/factions/kingdom.md and clans.md (culture, mood), ${WT}/docs/research/audio-direction.md (music sections), ${WT}/docs/research/ip-safety.md §2.5, ${WT}/docs/design/juice/ui-camera-audio.md (MUS-* rows: how music is played, night filter, ducking, gaps).
TOOLS INSTALLED: fluidsynth 2.3 (render MIDI offline: fluidsynth -ni -F out.wav -r 48000 -g <gain> <sf2> <mid>), the General MIDI soundfont /usr/share/sounds/sf2/FluidR3_GM.sf2 (MIT licence), python3 with mido and numpy and PIL, ffmpeg/ffprobe (loudnorm, afir convolution, equalizer, acompressor, aecho, showspectrumpic, silencedetect). pip install other pure-python packages only if really needed (and record them for the session hook).
IP RULES (hard): never a franchise, game, studio, film, composer or performer name in any file, comment, prompt or commit message; never quote or paraphrase a melody from the reference game's soundtrack or any other existing tune: build every melody from OUR motifs (bible §10.2: the kingdom "Wheel" motif, the clans "Gong-Ring" motif) and new material. Respect the AVOID list (kingdom: no symphonic brass fanfare with big choir; clans: no taiko, no low-brass-plus-electric-guitar; nobody: no airy solo female voice with harp and flute as lead colour). Run python3 tools/ip/check_banned_terms.py in ${WT} before each commit.
QUALITY BAR: this must not sound like cheap General-MIDI. Use real compositional craft and production:
- Modal harmony as briefed (Mixolydian, Dorian...), drones, real phrase structure (4+4-bar antecedent/consequent periods), motif development (sequence, inversion, augmentation, rhythmic displacement, fragmentation), a counter-melody, call and response between instruments, a clear dynamic arc per piece, contrasting sections with different textures, a real ending.
- Performance: humanise timing (±5-15 ms, ensemble-consistent), velocity shaping per phrase, accents on strong beats, ghost notes in drums, small tempo breathing at phrase ends, legato by note overlap, CC11 expression swells on bowed/blown sustains, CC1/pitch-bend slides and grace notes / mordents on fiddles, rolls and flams on drums.
- Sound palette: prefer the soundfont's fiddle, viola, cello, contrabass (pizz/arco), dulcimer, banjo/koto/sitar-ish plucks for lutes, bagpipe, shanai, recorder/pan flute only as minor colour, french horn/trombone only as distant two-note calls (never fanfares), timpani sparingly, GM percussion (low/high toms, bass drum, snare with brushes/rolls, tambourine, claps). SYNTHESISE with numpy whatever the soundfont lacks or does badly and mix it as audio stems: bronze gongs (inharmonic partials, long decay, struck and bowed swells), the hurdy-gurdy drone (buzzy sawtooth drone with a trompette rasp), jaw harp, deep overtone drone/chant (formant-filtered low drone, wordless), frame drums (pitched membrane with skin noise), hand claps and stamps.
- Production: per-stem EQ, panning and a shared room/hall reverb (generate an impulse response with numpy, apply with ffmpeg afir), gentle bus compression, master to about -16 LUFS integrated, true peak ≤ -1 dBTP, 48 kHz stereo, Ogg Vorbis -q:a 6. Background music for an RTS: mid-level dynamics, never piercing, leave room for unit voices around 1-3 kHz (gentle dip).
- Determinism: every piece is a Python source file that regenerates byte-identical MIDI and stems from a fixed seed; the rendered .ogg is committed.
SELF-CHECK (you cannot listen, so measure and LOOK): render a spectrogram PNG (ffmpeg showspectrumpic) and a piano-roll PNG of the MIDI (draw with PIL, one colour per instrument, section markers) for every piece and LOOK at both with the Read tool: check density, register spread, section contrast, no empty or mud-filled spans, clean ending. Measure loudness (ffmpeg loudnorm print_format=json), peak, duration, and for loops the seam (RMS and spectral difference across the loop point). Fix what looks wrong before committing.
COMMITS: commit EARLY AND OFTEN with clear messages on ${MB}; never push; never rewrite history. A usage limit can kill you at any moment.
`

phase('Toolkit')
const toolkit = await agent(`${ENV}
YOU ARE THE TOOLKIT AGENT. Build the reusable composition and rendering toolkit under ${WT}/tools/music/ (Python, documented, with --help on every CLI):
1. score.py: a small, pleasant API for writing pieces: tempo map, meter (incl. 6/8 over 4/4 feel), modes/scales and modal chords, motifs as objects with transforms (transpose in-mode, invert, retrograde, augment, diminish, displace, fragment, ornament), section builder, per-instrument tracks with articulations (legato, staccato, slides, grace notes, rolls), expression CC curves, humanisation (seeded), MIDI export via mido. Each instrument maps to a GM program OR to a numpy synth.
2. synths.py: numpy instruments rendered as audio stems from the same note events: bronze gong (struck + bowed swell), hurdy-gurdy drone + trompette buzz, jaw harp, overtone drone/wordless chant, frame drum, claps/stamps, bell (small town bell). Seeded and deterministic.
3. render.py: renders a piece module to stems (fluidsynth per stem group so each can be EQ'd/panned; numpy stems), mixes with ffmpeg (EQ, pan, reverb via generated IR with afir, bus compression), masters (loudnorm two-pass to -16 LUFS, -1 dBTP), exports Ogg Vorbis -q:a 6 48 kHz stereo; options --length-check, --loop (crossfade end into start 2-4 s for loopable pieces), --trim (for the 2.4 s opening cue with a 300 ms fade). Writes the spectrogram PNG and piano-roll PNG to ${WT}/tests/output/music/ (git-ignored).
4. A 40-second STYLE TEST per faction (pieces/style_kingdom.py, pieces/style_clans.py) using the bible's palette, rendered and LOOKED at, to prove the sound is not cheap MIDI: tune the soundfont gain, velocity curves, reverb and the synth instruments until the spectrograms and measurements look like a balanced, warm folk-ensemble mix. Write down the tuned palette (programs, gains, pans, reverb sends, synth settings) in tools/music/palette.py so composers reuse it.
5. tools/music/README.md: how to write and render a piece, the palette, the checks. Add a short "Music toolkit" section to tools/README.md.
6. A headless-free python test: tools/music/test_determinism.sh renders the style test twice and compares hashes of MIDI and stems.
Commit on ${MB}. Final reply: toolkit API summary (the functions a composer calls, with a 15-line example piece), palette decisions, measurements of the style tests, spectrogram paths, known limitations.`, { label: 'music:toolkit', phase: 'Toolkit' })
if (!toolkit) throw new Error('Toolkit incomplete - resume later')

const GROUPS = [
  { key: 'kingdom', pieces: 'Kingdom 1 "Market-Day Muster" (kingdom_1.ogg), Kingdom 2 "Boards and Thunder" (kingdom_2.ogg), Kingdom 3 "Linden Curfew" (kingdom_3.ogg), Victory kingdom (victory_kingdom.ogg, 12 s), Defeat kingdom (defeat_kingdom.ogg, 12 s)' },
  { key: 'clans', pieces: 'Clans 1 "Herd Road" (clans_1.ogg), Clans 2 "The Gong-Ring Gathers" (clans_2.ogg), Clans 3 "Long Grass Gallop" (clans_3.ogg), Victory clans (victory_clans.ogg, 12 s), Defeat clans (defeat_clans.ogg, 12 s), Opening cue clans (opening_clans.ogg: compose a 10 s flourish, trim to 2.4 s with a 300 ms fade; the kingdom opening cue already exists as an AI recording, assets/audio/music/opening_kingdom.ogg: listen to its spectrogram and match its loudness and length)' },
  { key: 'shared', pieces: 'Menu "Two Roads" (menu.ogg, 1:45, loopable: crossfade the last 2-4 s into the start), End-screen bed "Two Roads (score)" (score.ogg, 75 s, loopable). Both must state the kingdom Wheel motif and the clans Gong-Ring motif in dialogue (two cultures meeting) and be the most memorable music in the game' },
]

const REVIEW = { type: 'object', properties: {
  verdict: { type: 'string', enum: ['ship', 'revise'] },
  findings: { type: 'array', items: { type: 'object', properties: {
    piece: { type: 'string' }, severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
    problem: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } },
    required: ['piece', 'severity', 'problem', 'evidence', 'fix'] } },
  strengths: { type: 'string' } }, required: ['verdict', 'findings', 'strengths'] }

const results = await pipeline(GROUPS,
  (g) => agent(`${ENV}
YOU ARE THE COMPOSER for the ${g.key} group. Toolkit summary from the toolkit agent:\n${toolkit}\n
Compose, render and self-check these pieces, each as ${WT}/tools/music/pieces/<file stem>.py (deterministic) rendered to ${WT}/assets/audio/music/<file>.ogg: ${g.pieces}.
Use the bible §10.3 brief of each piece as the musical brief (key, mode, tempo, instruments, mood, structure and length: in-game tracks 3:20-3:40, they do NOT loop; menu/score loop). Each piece must be clearly different from its siblings in tempo, texture, metre feel and melody, while the faction motif ties the set together. Write a 5-10 line composer's note per piece at the top of its source (form with bar numbers, motif use, orchestration arc).
Order: compose the 12 s stingers last; start with the piece you think matters most and fully finish it (render, LOOK at spectrogram and piano roll, measure, fix) before starting the next. Commit after each piece. If you need a toolkit change, add it in a NEW module (tools/music/ext_${g.key}.py) instead of editing the shared toolkit files.
Final reply: per piece: file, duration, LUFS, peak, form summary, motif use, the spectrogram and piano-roll paths, and anything you are unsure about.`, { label: `compose:${g.key}`, phase: 'Compose' }),
  (composed, g) => agent(`${ENV}
YOU ARE A DEMANDING MUSIC CRITIC AND GAME-AUDIO DIRECTOR (do not edit any files; scratch work only under ${WT}/tests/output/music/review_${g.key}/). Review the ${g.key} group: ${g.pieces}.
Composer's report:\n${composed}\n
For every piece: read its source and composer's note; analyse the MIDI (note density per section, register spread, repetition: longest literally repeated span, melodic range, rhythmic variety, harmonic rhythm, mode correctness against the brief, motif presence, ending); LOOK at the spectrogram and piano-roll PNGs (and render your own if missing); measure loudness, peak and duration against the bible; for loops measure the seam. Judge against the bible brief and the QUALITY BAR above: would this be good background music for a classic fantasy RTS played for an hour (not tiring, not cheesy, not muddy, not empty, with a melody worth remembering)? Does anything resemble the AVOID list or a well-known existing tune (name the risk without naming any franchise in files)? Are the siblings distinct?
Return verdict 'ship' only if there are no blocker or major findings. Every finding needs evidence (bar numbers, seconds, measurements) and a concrete fix.`, { label: `review:${g.key}`, phase: 'Review', schema: REVIEW }),
  (review, g) => (review && review.findings && review.findings.length) ? agent(`${ENV}
YOU ARE THE COMPOSER for the ${g.key} group, revising after review. Fix every blocker and major finding and the cheap minors, re-render, LOOK at the new spectrograms and piano rolls, re-measure, commit after each piece.
REVIEW (verdict ${review.verdict}):\n${JSON.stringify(review, null, 1)}\n
Final reply: per finding fixed/skipped (with why), final per-piece table (file, duration, LUFS, peak).`, { label: `revise:${g.key}`, phase: 'Revise' }) : (review ? `no findings: ${review.strengths}` : null),
)
if (results.some(r => !r)) throw new Error('Compose/review/revise incomplete for a group - resume later')

phase('Integrate')
const integ = await agent(`${ENV}
YOU ARE THE INTEGRATION AGENT for the composed music on ${MB} in ${WT}.
Group results:\n${results.map((r, i) => GROUPS[i].key + ':\n' + r).join('\n\n')}\n
1. Verify every expected file exists in assets/audio/music: kingdom_1..3, clans_1..3, menu, score, victory_kingdom, victory_clans, defeat_kingdom, defeat_clans, opening_clans (plus the existing opening_kingdom from AI). Each decodes, 48 kHz stereo Ogg, -16 LUFS ±1, true peak ≤ -1 dBTP, duration within the bible (in-game 3:20-3:40, menu 1:45, score 75 s, stingers about 12 s, opening 2.4 s), no leading silence over 50 ms, menu and score loop seams clean.
2. Rewrite assets/audio/music/manifest.json for all pieces: id, file (res:// path), faction, kind (ingame|menu|score|victory|defeat|opening), loop (bool), duration, source (tools/music/pieces/<id>.py, or "ai" with the job id for opening_kingdom). Make the Godot .import for menu.ogg and score.ogg loop (and the others not loop): run "godot --headless --path ${WT} --import" once and commit the .import files.
3. Determinism: re-render two pieces from source in a temp dir and compare the MIDI hashes with the committed sources' output.
4. assets/audio/CREDITS.md: add FluidR3_GM soundfont (MIT licence, the instruments used to render the music), and that the music is composed by the project with tools/music. docs/asset-ledger.md: a row "2026-10-20, composed music, 0 CU". art-and-audio-bible.md §10: add a short note at the top of §10 that the music is now composed in-house with tools/music (the §10.3 prompts remain as the musical briefs), and §11's music budget line becomes 0.
5. Session hook: add fluidsynth and fluid-soundfont-gm (apt) and mido (pip) to ${WT}/.claude/hooks/session-start.sh in the same style as the existing installs (idempotent, quiet).
6. python3 tools/ip/check_banned_terms.py must pass; the repo's Godot tests are not affected (no src changes), do not run them.
Commit on ${MB}. Do NOT merge into the main branch (the orchestrator does). Final reply: the final table (piece, duration, LUFS, peak, loop), what changed, anything the Audio autoload must do (playlist per faction with 20-40 s gaps, menu/score loop, victory/defeat stinger crossfading into score, opening cue at match start).`, { label: 'music:integrate', phase: 'Integrate' })
if (!integ) throw new Error('Integration incomplete - resume later')
return { toolkit, results, integ }
