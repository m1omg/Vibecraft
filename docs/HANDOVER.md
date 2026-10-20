# Vibecraft handover

Read this first if you are a new Claude session picking up the project. Last updated 2026-10-20, after Playtest 1 shipped.

## 1. What this is

**Vibecraft** is a 3D, top-down hero RTS in **Godot 4.7.2** that plays as close to the classic 2002 hero-RTS (the user's favourite
childhood game) as is legally possible. Gameplay, structure and feel follow it closely. All names, art, audio and text are 100 %
original (`docs/research/ip-safety.md`).

- Slice factions: the **Brennmark kingdom** (guild townsfolk, wagons, early gunpowder) against the **Tormai clans** (courteous nomad
  households, felt yurts, bronze gongs). Forest-elf and undead-like factions come later.
- Repo `m1omg/Vibecraft`. Dev branch **`claude/clever-heisenberg-i8649y`**: work, commit and push here. No PR unless the user asks.

## 2. The user: how they want to work

- **Juice matters most.** Earlier attempts with other AI models were "generic, feel-less AI slop". Every click, hit, chop, build and
  level-up must feel great (`docs/design/juice-bible.md`).
- **Playtest per milestone.** When something is playable, verify it yourself (tests pass, a full match runs with no errors), then ask
  the user to PLAY-TEST it. Send screenshots, simple run steps, controls, what to try, known issues and questions. Don't just send
  screenshots.
- The user is busy with other projects. **Message them only with playtest requests** (and answers when they ask). Keep messages short.
- **Run steps for the user:** the ZIP download link
  `https://github.com/m1omg/Vibecraft/archive/refs/heads/claude/clever-heisenberg-i8649y.zip`, then Godot 4.7.2 → Import →
  `project.godot` → F5. They are not a git user.
- **Software must not depend on the display refresh rate** (hard requirement).
- **Ultracode:** use the Workflow tool (multi-agent) for substantive tasks. The scripts used so far are in `docs/workflows/`.
- Pause and resume times are given in **Bratislava time** (CET/CEST). Use `send_later` to schedule a resume when asked to pause.
- **Usage limits** interrupt often. Agents must commit early and often. Workflows need stage guards
  (`if (!x) throw new Error('... resume later')`) and a RESUME RULE in every prompt (see `docs/workflows/pt1-battlefield-sandbox.js`).
- Don't repeatedly tell the user they have no credits. Don't lecture about repo visibility. The "-craft" name is fine.
- Answer truthfully. Web-search facts about modern apps and prices. Double-check the user's corrections.

## 3. Current state (2026-10-20)

- **Playtest 1 "Battlefield Sandbox" shipped and is waiting for the user's feedback.** See `PLAYTEST.md`. Main menu → sandbox on
  the Wether Downs slice map: a static kingdom base and army against a scripted Tormai guard and war-band, three creep camps, and a
  victory/defeat banner. Full classic controls. 213 headless tests pass.
- **Engine:**
  - Fixed 30 Hz sim with physics interpolation, data-driven through the `Defs` autoload.
  - AStarGrid2D pathing on 0.5 m cells with group pathing; a spatial hash.
  - Painted terrain, cliffs, water and trees.
  - GLB unit views with clip sync.
  - Juice core: fx clock, VFX pools, order markers, selection rings, health ghost bars, hit-pause, camera impulses.
  - A manifest-driven Audio director.
- **The M2 contract is in place:** full slice data tables in `data/*.json` (`data/SCHEMA.md`), order handlers, and system stubs with
  documented APIs. Ownership map: `docs/m2-ownership.md`.
- **Art:**
  - **Units:** 12 rigged units (`assets/models/units`). The rig is our free autorigger `tools/autorig.py` plus licensed library clips.
  - **Buildings:** two AI-modelled halls, plus 19 procedural buildings and 47 doodads/neutral structures from Blender kits
    (`tools/kits/`).
  - **Terrain:** Greenvale textures.
- **Audio:**
  - SFX for combat, ranged and UI: Seed Audio plus Kenney CC0 (`assets/audio/CREDITS.md`).
  - Voice: tier-a acks (ready, what, yes, attack) for the hodman, pavisier, hookgunner, yurtwright and grappler. The script for the
    whole cast is in `docs/design/voice-lines.md`.
  - **Music: composed in-house**, 13 pieces, with `tools/music` (fluidsynth + FluidR3_GM, MIT, + numpy synths). The `music/p0` branch
    was finishing integration when this was written. If it is not yet merged into the dev branch, merge it. If `/tmp/vc_music` is
    gone, the dev branch has a checkpoint merge (57ecfa3) and the pieces can be re-rendered from `tools/music/pieces/*.py`.
    **Music is not yet wired to play in-game**: that needs per-faction playlists with 20–40 s gaps, menu/score loops and the
    victory/defeat stingers (juice MUS-* rows).

## 4. Next steps

1. Fold in the user's **Playtest 1 feedback**. Also ask how the three music tracks sounded.
2. Wire the music playback (above).
3. **Playtest 2 "Base building":** economy (gold mining, lumber), construction, production, upkeep, tech tiers, full HUD and command
   card. Adapt subsystem prompts A–H from `docs/workflows/m2-gameplay-build.js` and `docs/m2-ownership.md`.
4. **Playtest 3 "Heroes & creeps":** heroes, abilities, buffs, creeps, items, shops, fog of war, real minimap.
5. **Playtest 4 "Versus AI":** the AI opponent, a full juice pass, review and fixes.
6. **Asset requests** (QA and contract agents):
   - repaint the team-colour masks (most kingdom units are at 1–5 %, the Wheel Marshal at 38 %; run
     `tools/assets/check_team_coverage.gd`);
   - a Pavisier model;
   - creep models (Sootcoats, Harvest Folk, Cairnwakes);
   - siege carts (Bombard Wagon, Sling-Cart, Grand Bombard);
   - Hail-Swifts and critters;
   - the Coaching Inn;
   - projectile meshes;
   - icons, hero portraits and UI art (art bible §11);
   - voice for the rest of the cast.

## 5. Paid generation: budgets and rules

The full log is in `docs/asset-ledger.md`. **Log every paid job there**, including failures.

- **Balances (2026-10-20):** Krea **719.98 CU**, Higgsfield **77.35 cr**.
- **Higgsfield** is for what only it does well:
  - `tripo_h3_1_image_to_3d`: 9 cr, characters and buildings (raw output faces +X);
  - `3d_rigging` + clip: 8 cr (we mostly use the free autorigger now);
  - `gpt_image_2_5` images: 0.25 cr, for concepts and textures.
  - Submit 2–3 images at a time (429 rate limits are not charged).
- **Krea** is for 2D and audio:
  - Krea 2 Medium images: 9 CU;
  - ElevenLabs TTS: 2/27 CU per prompt character;
  - Seed Audio: ≈ 1.83 CU per second of output.
- **Banned:**
  - Krea music: about 444 CU for 10 s. Compose with `tools/music` instead.
  - Krea 3D models other than TRELLIS (148–222 CU).
  - TRELLIS for anything seen from the back (black sides).
- Always submit 3D/audio jobs **async** and log the job id immediately. Use `preflight`/`get_cost` first. When the quote is null,
  probe with the smallest possible job.
- The user asked for **the cheaper options**.

## 6. How to work in this repo

- **Engine contract:** `docs/architecture.md`.
- **Design:** `docs/design/` (gdd, rules, factions, neutrals, slice-plan, art-and-audio bible, juice bible + `juice/`).
- **Research:** `docs/research/`.
- **Source of truth when docs disagree:** `slice-content.json` > `gdd.md` > `rules.md` > faction docs / `neutrals.md` >
  `slice-plan.md` > art-and-audio bible > juice docs > `architecture.md`.
- **Tests:** `godot --headless --path . --import`, then `godot --headless --path . -s tests/run_tests.gd`. All must pass. Never
  skip or disable a test.
- **Screenshots:** `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1600x900x24" godot --path .
  --rendering-driver vulkan --audio-driver Dummy --resolution 1280x720 -s tests/playtest/pt1_sandbox.gd`. Software rendering runs
  at about 1–2 fps. LOOK at the PNGs.
- **IP checks** before every commit: `python3 tools/ip/check_banned_terms.py` and `tools/ip/check_value_echo.py`. Never use the
  reference game's names, lines, melodies or designs anywhere outside `docs/`.
- **Session setup:** `.claude/hooks/session-start.sh` installs Godot 4.7.2, lavapipe/xvfb, Blender bpy (`/opt/bpyenv`),
  fluidsynth + soundfont + mido, then imports the project.
- **Asset tools:** `tools/README.md`. `process_model.py`, `autorig.py`, `render_preview.py`, the `kits/` Blender generators, `audio/`
  and `music/`.
- **Raw paid outputs** live in `assets_src/` (it has a `.gdignore`).
- **Workflows:**
  - Concurrency is capped at 2 agents per workflow (4 CPUs).
  - Parallel agents use git worktrees under `/tmp/vc_*` on local branches, then merge into the dev branch.
  - Container files outside git can be lost when the VM is reclaimed: commit and push anything worth keeping.
