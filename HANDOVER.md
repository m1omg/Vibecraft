# Vibecraft handover

Read this first if you are a new Claude session picking up the project. Last updated 2026-10-30. Playtest 3 has shipped
(2026-10-30); no feedback on Playtest 2 or 3 has come in yet.

## 1. What this is

**Vibecraft** is a 3D, top-down hero RTS in **Godot 4.7.2** that plays as close to the classic 2002 hero-RTS (the user's favourite
childhood game) as is legally possible. Gameplay, structure and feel follow it closely. All names, art, audio and text are 100 %
original (`docs/research/ip-safety.md`).

- Slice factions: the **Brennmark kingdom** (guild townsfolk, wagons, early gunpowder) against the **Tormai clans** (courteous nomad
  households, felt yurts, bronze gongs). Forest-elf and undead-like factions come later.
- Repo `m1omg/Vibecraft`. Dev branch **`claude/clever-heisenberg-i8649y`**: work, commit and push here. Playtest 2 was built on
  `claude/bold-johnson-kpuvf2` and merged back into it on 2026-10-30. No PR unless the user asks.
- The code is all **GDScript** (≈ 200 files) plus Godot shaders, with **no C#**, so the standard (non-.NET) Godot build runs it. The
  Python in `tools/` (Blender kits, autorig, audio, music) is offline asset tooling and never ships with the game.

## 2. The user: how they want to work

- **Juice matters most.** Earlier attempts with other AI models were "generic, feel-less AI slop". Every click, hit, chop, build and
  level-up must feel great (`docs/design/juice-bible.md`).
- **Playtest per milestone.** When something is playable, verify it yourself (tests pass, a full match runs with no errors), then ask
  the user to PLAY-TEST it. Send screenshots, simple run steps, controls, what to try, known issues and questions. Don't just send
  screenshots.
- The user is busy with other projects. **Message them only with playtest requests** (and answers when they ask). Keep messages short.
- **Run steps for the user:** the ZIP download link of the branch they should play, now
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

## 3. Current state (2026-10-30)

- **Playtest 3 "Heroes and creeps" shipped and is waiting for the user's feedback** (`PLAYTEST.md`; it also repeats the open
  Playtest 2 questions). The same Skirmish on Wether Downs, now with heroes and creeps on both sides. ≈ 330 headless tests pass
  (the full run takes about 4 minutes). What it added (architecture §10–§11 has the contracts):
  - **Heroes** (`heroes.gd`): kill XP shared within 18.75 m (creep factor, single-hero bonus), level-ups, proper names, the Learn
    page, death records, the altar revive (a Production queue entry) and the inn revive; the hero bar (top left) and the info
    panel's XP and attributes.
  - **Casting** (`abilities.gd`, `buffs.gd`, `combat.gd`): cast point / backswing / channel / cancel rules, mana and cooldowns
    spent at the cast point, auras and passives, buffs (refresh, hero control durations, DoTs / HoTs, breaks, dispel), natural
    regeneration (it was missing before), the damage pipeline (damage %, PRD crits and misses, damage taken), invisibility
    through `Fog.can_see`, ground effects; the card's ability buttons (cooldown sweeps, mana shortfall, targeting with an area
    ring).
  - **The 16 slice hero abilities** with their effects, tooltips (`ability_<id>` strings filled per rank) and a first juice
    pass (`hero_fx.gd`, `hero_sigils.gd`, `xp_motes.gd`, `ability_fx.gd`; procedural sounds in `assets/audio/sfx/heroes`).
  - **Creeps** (`creeps.gd`): bounty, drops, night sleep with a seeded stagger, invulnerable full-heal returns, the give-up
    timer, the creep spell AI (`SpellAi`), creep passives and auras.
  - **Items and shops** (`items.gd`, `shops.gd`, `inventory_panel.gd`): permanent item stats, charge merging, the recall
    channel, the first hero's recall item, shop cards (own and neutral), restock, Fair Exchange, the inn revive; numpad
    item keys.
  - **Worker defence:** the Levy Horn / Flail Levies (kingdom), Sound the Gong / Home Yurt garrisons (clans).
  - **The computer** learns from each hero's `skill_build`, casts through `SpellAi`, drinks potions, revives at the altar,
    creeps along the map's `creep_route`, and calls its worker defence.
  - Screenshots: `tests/playtest/pt3_heroes.gd` (learn page, altar revive, level-up, abilities, inventory, shop).
- **Playtest 2 "Base building" (2026-10-21):** Skirmish (faction and computer difficulty toggles) on Wether Downs from one hall and
  five workers, against the build-order computer; the Playtest 1 Battlefield Sandbox is still in the menu.
- **Fullscreen by default (2026-10-30, asked for by the user; announced with Playtest 3):** the
  game opens in borderless fullscreen at the monitor's resolution (`window/size/mode=3`). Alt+Enter or F11 (`toggle_fullscreen`,
  handled by the `Settings` autoload, which keeps processing in menus and while paused) switches to a resizable 1600×900 window
  centred on the screen and back. The choice is saved as `Settings.window_mode` in `user://settings.cfg` and re-applied at start
  (`tests/unit/test_window.gd`). The 1600×900 viewport stays the UI design size (`canvas_items` + `expand`). Later: a settings
  screen (window mode, resolution, vsync, UI scale, audio volumes).
- **Playtest 1 feedback, done:** fog of war (per-team 2 m vision grids, cliffs and trees block sight, hidden enemies, building ghosts,
  terrain/water/foliage/minimap fog) and a real Bombard Wagon (and Sling-Cart) model: procedural Blender kit `tools/kits/siege.py`,
  rolling wheels, crew, recoil and throwing-arm motion (`src/fx/vehicle_rig.gd`).
- **Since Playtest 1 (built on `claude/bold-johnson-kpuvf2`, now merged into the dev branch):**
  - **Music wired** (`src/audio/music_director.gd`): menu loop, the faction rotation with 20–40 s gaps, stinger then score bed;
    juice §5.1 bus levels (the "mix change" the playtest asks about).
  - **Economy** (`src/systems/economy.gd`): the gold seam door queue (one worker inside, 1 s dwell, 10 gold), five workers saturate,
    lumber trips per faction with felling and retargeting, Return Cargo resuming the last job, upkeep tax, seam depletion.
  - **Construction** (`construction.gd`): cost checked on order and paid on arrival, sites rising from 10 % HP, the kingdom's Hod
    Chain, cancel 75 %, repair; `cell_states` is the per-cell placement rule that `can_place` and the build ghost share;
    `Tech.can_build` gates menus, tier and requirements.
  - **Production and tech** (`production.gd`, `tech.gd`): queues of 7 for units, research and building upgrades, first hero free,
    hero slots by tier, supply stalls with a notice, hall and Lookout upgrades transforming in place, research effects on living and
    new units.
  - **HUD** (`src/ui/`): `CardModel` (the card as data: worker card, build pages, building cards), `CardButton` availability
    states, `BuildPlacement` sketch ghost and cell grid, `QueuePanel`, `HudTooltip`, `ErrorLine`, `IdleWorkerButton`, rolling
    resource counters, the upkeep flip. Architecture §11 documents them.
  - **Skirmish:** `AiPlayer` is a Playtest 2 build-order opponent driven by `factions.<id>.ai_opening` (workers, supply, the
    opening's steps, army mix, defend, push, retreat); `MatchRules` ends the match (no structures = defeated, cripple reveal).
  - **Economy and building juice** (`src/fx/build_fx.gd`): stamp, hammer / mallet and chop strokes on the work clip's contact,
    completion and tier-up flourishes, food popups, tree falls, deliveries, cave-ins; new CC0 + procedural sounds built by
    `tools/audio/build_layered_sfx.py` (recipes in `gen_layered_recipes.py`), no paid jobs.
- **Engine:**
  - Fixed 30 Hz sim with physics interpolation, data-driven through the `Defs` autoload.
  - AStarGrid2D pathing on 0.5 m cells with group pathing; a spatial hash.
  - Painted terrain, cliffs, water and trees.
  - GLB unit views with clip sync.
  - Juice core: fx clock, VFX pools, order markers, selection rings, health ghost bars, hit-pause, camera impulses.
  - A manifest-driven Audio director.
- **The M2 contract is in place:** full slice data tables in `data/*.json` (`data/SCHEMA.md`), order handlers, and system stubs with
  documented APIs. Ownership map: `docs/m2-ownership.md`. Still stubs: heroes (XP, levels, revive), most ability effects (the faction
  signatures among them), items, shops, creep sleep/bounty.
- **Art:**
  - **Units:** 12 rigged units (`assets/models/units`) plus the two siege vehicles (`assets/models/vehicles`). The rig is our free
    autorigger `tools/autorig.py` plus licensed library clips.
  - **Buildings:** two AI-modelled halls, plus 19 procedural buildings and 47 doodads/neutral structures from Blender kits
    (`tools/kits/`).
  - **Terrain:** Greenvale textures.
- **Audio:**
  - SFX for combat, ranged and UI: Seed Audio plus Kenney CC0 (`assets/audio/CREDITS.md`); economy and building sounds are CC0 layers
    plus procedural bronze bowls (`assets/audio/sfx/world/`).
  - Voice: tier-a acks (ready, what, yes, attack) for the hodman, pavisier, hookgunner, yurtwright and grappler. The script for the
    whole cast is in `docs/design/voice-lines.md`.
  - **Music: composed in-house** with `tools/music` (13 pieces), all wired now. The two-person listening check from the bible is still
    pending: the playtest asks the user.

## 4. Next steps

1. Fold in the user's **Playtest 2 and 3 feedback** (the questions are in `PLAYTEST.md`; the Playtest 2 mix and music answers
   matter).
2. **Playtest 4 "Versus AI":** the rest of rules §19 for the computer (shops and potions, the recall item, expansions, focus fire,
   hero micro and retreat on Hard, contested camps, scouting), a full juice pass (the remaining HER-01..08 and ABL rows, the
   economy/building juice still listed in `docs/design/juice/economy-and-buildings.md`), review and fixes. Gaps left by Playtest 3:
   autocast on the card (right click), item drag and drop, selling items in the interface, the laptop item keys (Alt + 1–6 clash
   with control groups), inn heroes (hiring), conditional creep passives (Stand Still, Settle), Swallowed Sun blocking sight
   lines, the Levy Horn on the tier-2 Walled Burg (its def has no abilities), a settings screen.
3. **Asset requests** (QA and contract agents):
   - repaint the team-colour masks (most kingdom units are at 1–5 %, the Wheel Marshal at 38 %; run
     `tools/assets/check_team_coverage.gd`);
   - a Pavisier model;
   - creep models (Sootcoats, Harvest Folk, Cairnwakes);
   - the Grand Bombard (the Bombard Wagon and Sling-Cart now have procedural models) and a Flail Levy look (it uses the Hodman
     model);
   - Hail-Swifts and critters;
   - item icons and ground props (the oilcloth bundle, power-up props; neutrals §1.8);
   - the Coaching Inn;
   - projectile meshes;
   - icons, hero portraits and UI art (art bible §11): the command card and queue still show names and initials;
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
- **Screenshots:** `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1280x720x24" godot --path .
  --rendering-driver vulkan --audio-driver Dummy -s tests/playtest/pt1_sandbox.gd`. The game starts fullscreen, so a capture is
  the size of the Xvfb screen: Godot ignores `--windowed` and `--resolution` then. Software rendering runs at about 1–2 fps. LOOK
  at the PNGs.
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
