# Vibecraft handover

Read this first if you are a new Claude session picking up the project. Last updated 2026-10-30. Playtest 1 has shipped; no feedback
has come in yet.

## 1. What this is

**Vibecraft** is a 3D, top-down hero RTS in **Godot 4.7.2** that plays as close to the classic 2002 hero-RTS (the user's favourite
childhood game) as is legally possible. Gameplay, structure and feel follow it closely. All names, art, audio and text are 100 %
original (`docs/research/ip-safety.md`).

- Slice factions: the **Brennmark kingdom** (guild townsfolk, wagons, early gunpowder) against the **Tormai clans** (courteous nomad
  households, felt yurts, bronze gongs). Forest-elf and undead-like factions come later.
- Repo `m1omg/Vibecraft`. Dev branch **`claude/clever-heisenberg-i8649y`**: work, commit and push here. No PR unless the user asks.
- The code is all **GDScript** (≈ 180 files) plus Godot shaders, with **no C#**, so the standard (non-.NET) Godot build runs it. The
  Python in `tools/` (Blender kits, autorig, audio, music) is offline asset tooling and never ships with the game.

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
- **Usage is the constraint now.** The user is NOT using ultracode any more: multi-agent workflows used 1–3 million tokens each.
  Work directly in the session by default. Use a single subagent or a small workflow (2–3 agents, no critic/judge loops) only for
  big, clearly parallel chunks, and only when the user agrees. The scripts used so far are in `docs/workflows/` for reference.
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
  - **Music: composed in-house** with `tools/music` (fluidsynth + FluidR3_GM, MIT, + numpy synths): 13 pieces (kingdom 1–3, clans
    1–3, menu, score bed, victory/defeat ×2, clans opening cue), merged in eacaad7. Manifest: `assets/audio/music/manifest.json`.
    The Audio director already plays the opening cues and the victory/defeat stingers.
  - **Not wired yet:**
    - the in-game playlist: per faction, shuffled, 20–40 s gaps, first track 6 s after the opening cue;
    - the menu loop;
    - the score bed after the stinger.
    `tools/music/README.md` "In the game" and the juice MUS-* rows give the spec. The two-person listening check from the bible is
    still pending: ask the user.

## 4. Next steps

1. **Fullscreen by default (asked for by the user; do this first).** The game currently opens in a 1600×900 window, and there is no
   fullscreen option. `project.godot` has `window/size/viewport_width=1600`, `viewport_height=900`, `resizable=true`, and stretch
   `canvas_items` / `expand`.
   - **Default mode:** start in **borderless fullscreen at the monitor's native resolution**. Set `window/size/mode=3`
     (`DisplayServer.WINDOW_MODE_FULLSCREEN`, borderless; not 4, exclusive).
   - **Keep the 1600×900 viewport** as the UI design size. With `canvas_items` + `expand`, the HUD scales and the 3D view renders
     at the real window resolution. Wider and taller screens show more map.
   - **Toggle with Alt+Enter and F11.** Add a `toggle_fullscreen` action to `Settings.default_actions()` in
     `src/autoload/settings.gd`. Handle it in a node that keeps processing while the game is paused: the Settings autoload with
     `process_mode = PROCESS_MODE_ALWAYS`, using `_unhandled_input`, so the toggle also works in the main menu and the F10 pause
     menu.
   - **Windowed size:** going windowed restores a 1600×900 window centred on the current screen, still resizable.
   - **Remember the choice:** persist it as `window_mode` (`"fullscreen"` / `"windowed"`) in `user://settings.cfg` via `_PERSISTED`,
     and apply it in `Settings._ready()` after `load_settings()`.
   - **Headless:** skip all `DisplayServer` window calls when `DisplayServer.get_name() == "headless"` so the headless tests are
     unaffected.
   - **Screenshot scripts:** under Xvfb a fullscreen window would take the Xvfb screen size (1600×900) instead of
     `--resolution 1280x720`. Add Godot's `--windowed` flag to every screenshot command, in §6 below, in the `## Run` comments of
     `tests/playtest/*.gd`, and in `tools/README.md`.
   - **Test:** a unit test that the toggle flips and persists `window_mode`, with the `DisplayServer` calls guarded.
   - **Docs:** add "Fullscreen / window: Alt+Enter or F11" to the controls table in `PLAYTEST.md`, and the action to
     `docs/architecture.md` §11. Mention it in the next playtest message.
   - **Later:** a proper settings screen (window mode, resolution, vsync, UI scale, audio volumes) with the PT2 HUD work.
2. Fold in the user's **Playtest 1 feedback** when it arrives. Also ask how the three music tracks sounded (menu, Kingdom 1,
   Clans 1 were sent).
3. Wire the music playback (§3 "Not wired yet").
4. **Playtest 2 "Base building":** economy (gold mining, lumber), construction, production, upkeep, tech tiers, full HUD and command
   card. Adapt subsystem prompts A–H from `docs/workflows/m2-gameplay-build.js` and `docs/m2-ownership.md`.
5. **Playtest 3 "Heroes & creeps":** heroes, abilities, buffs, creeps, items, shops, fog of war, real minimap.
6. **Playtest 4 "Versus AI":** the AI opponent, a full juice pass, review and fixes.
7. **Asset requests** (QA and contract agents):
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
  --rendering-driver vulkan --audio-driver Dummy --resolution 1280x720 -s tests/playtest/pt1_sandbox.gd`. Add `--windowed` once the
  fullscreen default (§4 step 1) is in. Software rendering runs at about 1–2 fps. LOOK at the PNGs.
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
