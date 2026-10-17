# Vibecraft Juice Bible

*The cross-domain game-feel contract for Vibecraft. Date: 2026-10-17. Status: revision 1, ready to implement. It sits above the five domain juice docs. Where they disagree, Appendix A rules. Where this bible promotes a P1 item to P0, §3.0 says why.*

**What this document is.** It answers four questions for anyone touching feel: what we believe (§1), which twelve moments must land at the vertical slice and exactly how, frame by frame (§2), what must be built for the slice and where in the code (§3, §4), and how we prove it works (§5). Every number here is either restated from a domain doc, with its feature id, or marked as a bible ruling.

**The domain docs** (feature-id prefixes in brackets):

| short name | file | ids |
|---|---|---|
| combat | `docs/design/juice/combat-and-units.md` | FND-1..7, CMB-01..46 |
| economy | `docs/design/juice/economy-and-buildings.md` | ECO-01..31, BLD-01..26 |
| heroes | `docs/design/juice/heroes-abilities-vfx.md` | HVF-1..8, HER, ABL, STS, SUM, ITM, CRP, ULT |
| world | `docs/design/juice/world-and-atmosphere.md` | WLD-F1..F6, WLD-01..48 |
| ui | `docs/design/juice/ui-camera-audio.md` | UCA-F1..F5, CAM, CUR, SEL, HUD, NTF, POR, GRP, SEQ, AUD, MUS |

Research inputs: `docs/research/visual-art-direction.md` (the 15 rules; "storm-lit hand-painted heroic diorama"; only VFX bloom), `docs/research/audio-direction.md` (the 14 rules; acks are 2D; caps; music with silences), `docs/research/video-references.md` §G (WC3 key moments, written here as *video M1–M17* so they are not confused with this bible's SM-01..12), `docs/research/godot-rts-tech.md`, `docs/architecture.md` (30 Hz fixed sim, physics interpolation, `display_pos()`, runs without art).

**Notation** (the same as the domain docs). Durations are ms at 1× game speed. `f60` is the frame index at 60 Hz (t / 16.7 ms), given so a reviewer can frame-step a clip. Distances are metres; `h` is unit height. Colours are sRGB hex; "HDR n" is an emission multiplier and only n > 1 blooms. Easings are the Penner set in `Juice` (combat FND-1). "Own" means the local player. **★** marks a twist WC3 did not have (in feature names) or a **bible promotion to P0** (in §2 and §3). "(P1)" or "(P2)" inside a P0 sheet marks a beat that is not slice-critical. The slice is `kingdom` (Brennmark) vs `clans` (the Tormai; the UI never shows "Clans").

---

## 1. Philosophy

### 1.1 What "juice" means in Vibecraft

Vibecraft is a **painted tin-soldier diorama that answers when spoken to, keeps time and never lies**. Our juice is *information in costume* (economy §1): each flourish answers a question the player is already asking (did they hear me? did that land? is my base healthy? when does that spell fire? is it night yet?), and answers it in the faction's own material and rhythm. It is *thwacky, not sparkly* (combat §1). WC3 read well because its feedback was short, chunky and sparse. We keep that restraint and put the craft into **timing, secondary motion, per-character beats and truthful tells**, not into particle counts.

The brief was to beat the generic, juiceless "AI clone" that earlier attempts produced. The clone has a recognisable signature, and every line of it is banned here:

| the AI-slop signature | the Vibecraft answer | where |
|---|---|---|
| one `out_back` pop on everything | faction motion dialects (kingdom stepped clockwork, Tormai wind and breath), material tokens (TIMBER_SNAP, FELT_BOB, STONE_THUD, BRONZE_RING), an overshoot budget for three UI families only | heroes §2.1 rule 14, economy §2.4, ui §2 |
| a glowing orb in the hand and a magic circle under every cast | props, release-class body poses and the sigil's own cast mode fill the cast point | ABL-01, HER-01 |
| a damage number on every hit | text policy *Minimal*; numbers merge; XP is never printed | CMB-28, HER-03 |
| decorative shockwave rings | a crisp ring always means a true radius of effect; cosmetic rings are ≤ 1.6 m, α ≤ 0.35, edgeless | heroes §1 rule 6, economy rule 8 |
| anonymous sparkles and "motes" | every particle is a named painted thing in the struck material | FND-2, HVF-5, combat §4.8 |
| screen shake for everything | an exhaustive whitelist, trauma², a directional kick; heavy moments get a sub-bass thump instead | ui §5.4, CAM-05, AUD-02 |
| free-running attack clips | the contact pose lands exactly on the sim's damage tick | CMB-16 |
| one death for every unit, a gold pillar for every level-up | death styles per material, four hero death silhouettes, an emblem that stands up to face you | CMB-30, HER-06, HER-04 |
| bloom on units and buildings | units ≤ 0.95 linear at peak flash; buildings never bloom; only VFX exceed 1.0 | CMB-17, BLD-15 |
| night as a dimmer switch | a nightfall tide sweeping across the field, landing on one downbeat | WLD-03, world §5.3 |
| a metronome base | every site on its own subdivision of the beat, every builder humanised, all in key | BLD-08 |
| skin-swap factions | material includes motion: the same time budget, different physics | ui §3.1, combat §4.9 |
| coin showers and slot-machine counters | habituated odometers; one sanctioned coin flight (local bounty) | ECO-13, CMB-28 |
| destruction as a dissolve or wipe | buildings cave in under their own weight | BLD-16 |
| stock noise dissolves and Bayer stealth | heroes are painted out stroke by stroke; invisible units are the painter's under-drawing | HVF-4 |
| a screensaver forest and wallpaper ambience | one wind with lag and recoil; beds ≥ 45 s; landmarks with their own life | WLD-10, world §8 |
| alarm spam and voice spam | one alarm per category per 8 s, a quiet path for what is on screen, order ticks instead of voices | NTF-01, AUD-03 |

### 1.2 The ten rules of Vibecraft juice

Each rule is binding on every domain doc, has numbers, and has a test (§5).

**Rule 1. Every command answers on the input frame, in three channels: sound, mark, motion.**
- **Sound:** a 2D ack line or a non-verbal order tick starts on the input frame, within one audio buffer (≈ 15 ms). Acks are 2D because a 3D player only starts on the next physics tick (AUD-03, ui §2).
- **Mark:** the order marker, the ring tint and the button press are drawn on the input frame from `ui_time` (CMB-08, CMB-10, HUD-01). The command card acts on the down-stroke.
- **Motion:** the first unit of the selection nods on the input frame. The ripple reaches the last unit by 308 ms (28 ms per rank). The sim moves the first unit within 3 ticks (≤ 100 ms) (CMB-10).
- The UI never waits for the sim, and spam never produces voice spam (order ticks, ≤ 1 nod per 450 ms per unit).
- *Test:* `test_command_latency.gd` (§5.2 G14).

**Rule 2. Every tell is a fact; the display never lies.**
- Quantities the player acts on (resources, HP and mana, cooldowns, supply, timers, radii) are exact on the event frame. Only trailing *ghosts* may lag (CMB-29, ECO-13, ui §2).
- A ceremonial picture of a discrete change (a level badge flip, a lit segment, a stamp) may take up to 350 ms to complete, but it never starts before the event. *(Bible ruling; it reconciles HER-04's badge flip with ui pillar 4.)*
- Radii are drawn on the sim's own metric, within ±2 % (`edge_distance` for halls). No fake blocks or parries. No ring that keeps promising what was decided at cast (ULT-02's hand-off).
- *Test:* `test_truthful_radii.gd`, `test_eco_rings.gd`, `test_ui_juice.gd`.

**Rule 3. Juice is a pure function of sim state and time. The sim never waits for it.**
- Read-only: no `World.rng`, no writes to `Unit` or `PlayerState`, no `Engine.time_scale` during play, no delayed events. Hit-stop is a hold on the attacker's *visual* pose only (CMB-16, ECO-08).
- The single exception is the post-match held breath (SEQ-02), which starts only after World stepping has halted.
- Refresh-rate proof by construction:
  - closed-form curves of age; exact springs (`Juice.spring`); `damp` instead of `lerp(a, b, k)`;
  - crossing tests for thresholds; back-dated accumulators for periodic spawns;
  - **latched peaks** (anything ≤ 60 ms starts at its peak);
  - stateless hashes for randomness;
  - pattern frequency ≤ 12 Hz (≤ 7.5 Hz for anything that must read as motion);
  - no shader `TIME`.
- *Test:* `test_juice_determinism.gd`, `test_juice_framerate.gd` (and the camera and atmos variants), clip parity at 30/60/144 fps (§5).

**Rule 4. Cause arrives with or before its effect, and lands on the tick.**
- The blade's contact pose is the damage tick (CMB-16). A spell's release spawns on the frame that processes `ability_released`, and travel visuals are pre-launched to arrive on that frame (ABL-01, heroes §2.1 rule 17).
- XP chips reach the hero before the level-up flare they cause (HER-03). A builder's last blow lands on the completion tick (BLD-24). A whoosh peaks on contact and a riser peaks on release (`peak_ms` in `data/sfx_meta.json`).
- Anticipation is built from *predictions* that degrade gracefully when they miss: deposit pre-wind (ECO-04), completion wind-up (BLD-24), mine exit glow (ECO-01).
- *Test:* `test_swing_pose.gd`, `test_spell_sync.gd`, the deposit-grid and completion tests (§5).

**Rule 5. Ceremony scales with rarity. Repeats get shorter, never longer.**

| event | frequency | ceremony |
|---|---|---|
| order, chop, hit | many per second | ≤ 0.5 s, mostly ≤ 0.3 s |
| deposit | ≈ 1 per s per mine | lands ≤ 0.5 s after the touch; popup 1 s; coins gone by 2.2 s |
| XP gain | every few seconds | ≤ 0.75 s (asserted) |
| potion, pickup, purchase | a few per game | ≤ 0.6 / 0.7 / 0.8 s |
| building complete | ≈ 1 per minute | ≤ 1 s (the banner flutter decays after) |
| hero level-up | 9 per game | 1.5 s (line at 1.15 s) |
| camp cleared | 5–7 per game | 1.6 s |
| hall tier-up | 1–2 per game | 1.8 s |
| destruction | rare | 1.4 / 2.2 / 3.4 s by size |
| ultimate | 2–5 per game | a 7–25 s set piece |
| match end | once | 8 s to the Chronicle, skippable |

- Habituation is specified, not hoped for: the mine door glow steps 1.6 → 1.3 → 1.1 (ECO-01); the ledger loses 1.5 dB per minute (ECO-25); a second destruction of the same def within 20 s plays the small variant (BLD-16).
- Teaching repeats then leaves: the tax peel teaches for 6 s (ECO-05), the creep-cap fizzle plays 3 times (HER-03), the [Space] hint shows 3 times (NTF-01).

**Rule 6. Readability beats spectacle.**
- Nothing covers a unit, its team colour, its ring or its health bar for more than **80 ms** (combat §2.2).
- Only VFX bloom. Unit flash peaks at linear luminance ≤ 0.95; unit and sigil rims ≤ 0.6; buildings never bloom (CMB-17, HER-01, BLD-15).
- Danger is never throttled: zone edges, CC glyphs, timers, hero events, rim flash, rings and bars always draw. Cosmetics thin first, **evenly for both sides** (FND-3).
- **Spectacle goes up, not out:** pillars, columns and standing emblems instead of wide rings (heroes §1 rule 6). Plumes are donuts and dust skips the spots where units stand (economy §2.8).
- The central 50 % of the playfield never gets HUD overlays during play (ui §2).
- Every state is shape-coded as well as colour-coded: notched = hostile or alert, dashed = hover or creep, hatched = unaffordable or low HP.
- Semantic tells move a silhouette edge ≥ 4 px at the default camera (28 m, FOV 45°, pitch −56°); world motion ≥ 1.5 px (L1, world §2).

**Rule 7. Personality is authored, never sprinkled.** Identical timing across characters is the slop signature (heroes §1 rule 8).
- Every slice unit has a motion sheet (combat §4.9).
- Every hero has its own cast props, level gesture, wear marks, death silhouette and denial gesture (HER-02..06).
- Every slice building has a select voice and a construction verb, and every production building has its own work loop (BLD-18, BLD-07K/C, BLD-11).
- **Faction = material + motion dialect** (combat §4.9 grammars, heroes §2.1 rule 14, ui §3.1):

| dialect | entrances | settles | waves |
|---|---|---|---|
| kingdom (Brennmark) | snap 40–60 ms `in_cubic`, then a hold | 3–4 % recoil, `out_back(2.0)`, 40–50 ms | step 20 ms per element |
| Tormai | swell 200–420 ms `in_out_sine` | low-damped sway, ω 6–9, ζ 0.25–0.35 | breathe 35 ms per element |
| neutral and creeps | stop-motion steps (2–3 held poses at 12 Hz) or plain `out_cubic` | none, or one `out_quad` bounce | — |

- Every number in a row comes from the unit's def `fx` block or from `FeelConstants` (§4.8), never from a house constant reused without reason.

**Rule 8. Fog-honest and fair.**
- No sprite, sound, shake, glance, ping, cursor change, preview, critter reaction or world memory comes from anything the local player cannot currently see, unless it is the player's own (combat §2.2, world §2, ui §2).
- Never shown to an opponent: enemy XP progress, ultimate readiness, learned skills, altar dressing, recall bearings, item carriers. Only the sim-driven Sparrow Roost flush (SLICE+) is drawn equally for all players.
- **One predicate decides visibility for every system** (Appendix A, R6).

**Rule 9. One clock, one wind, one key.**
- Time: `Clock.ui_now` and `Clock.fx_now` (ui §2), plus `sim_time` = (tick + lead) × DT for anything sim-bound (heroes §2.1). `hour` = `DayNight.hour_at(sim_time)`.
- One wind field with lag and recoil (WLD-10) and one sun (`atm_sun`) drive every blade, flag, smoke column and mirror glint.
- Pitched juice takes its notes from `MusicClock`'s pentatonic, so it never clashes with the score (economy §2.7). Hammers, deposits, work loops and level bells lock to its grid or ladder; chops and hits keep the sim's tempo and take only pitch.
- **Valence rule:** positive cues are consonant, single or rising. Alarms are dissonant, fast and falling, and use instrument families nothing positive uses (ui §5.3; Appendix A, R15).
- **Staging rule** (world §5.3, generalised by this bible): a big moment has **one downbeat**, where at most one headline element per channel (one World, one UI, one voice) lands on the same frame. Everything else cascades after it, 60–450 ms apart.

**Rule 10. The camera and the mix are the player's hands and ears.**
- The camera moves only when the player asks (pan, zoom, jump) or when a whitelisted ground-heaving event happens in view, ≤ 0.6 total trauma (ui §5.4). It never drifts, follows or auto-zooms.
- One ack voice at a time; alarms are throttled; off-screen sounds are muffled; Music is never more than 8 dB down during play (AUD-01..04).
- Music rotates with 20–40 s of silence between tracks (MUS-01).
- Heavy moments get a deliberate sub-bass thump on the `Sub` bus (AUD-02), not a shake.

---

## 2. Signature moments

These twelve moments must give a WC3 veteran goosebumps: each one is recognisably the convention they remember, and then does something WC3 never did. Each has:
- **Anchor:** what t = 0 is. It is always a sim event or an input event, never a juice timer.
- **Built from:** the feature ids that make it. ★ marks a bible promotion to P0 (§3.0); everything else listed is already P0 unless tagged (P1) or (P2).
- **Beat sheet:** the four channels (visual, audio, UI, camera), each a closed-form function of the anchor, so QA can assert every row from a trace (§5.4).
- **P0 floor:** what still has to land if every (P1) beat is missing.

| # | moment | anchor | WC3 memory (video ref) | our twist |
|---|---|---|---|---|
| SM-01 | The first command | box release, then right-click | acks and the ground blip (M10, M13) | rings paint in like ink; the order ripples through the selection |
| SM-02 | The first gold deposit | `resource_delivered` | the gold trip and the clink (M6) | Agnes tipped into the counting hatch on a 16th note; coins settle like coins |
| SM-03 | Tree felled | the felling strike's contact | the chop loop and the falling tree (M7) | the chop goes hollow in key; "Timber!"; it never falls toward you |
| SM-04 | The first building completed | `building_completed` | construction and the job-done line (M8) | an accelerando, and the final blow lands on the completion tick; scaffold "fwump" |
| SM-05 | First contact and the first fall | the first melee damage tick; then the first kill | the melee clash | blows land on the tick; a pavise splinters; the team colour drains like a lowered flag |
| SM-06 | Camp cleared | `camp_cleared` | creeping and bounty (M4, M15) | the bounties fly into one stamp; XP chips click into the wheel |
| SM-07 | Hero level-up | `hero_level_up` | the level-up flash (M1) | the emblem stands up to face you and ratchets one notch; the bell climbs the music |
| SM-08 | The ultimate: the Wagon Ring | `ability_released` | the ultimate | the roll call: twelve wheels race round and hand the protection to the soldiers they caught |
| SM-09 | Base under attack, and the horn | first hit on a worker off-screen; then the horn key | the alarm, the ping and the town-hall bell that arms the workers (M9, M14) | a panned alarm, "fights you started stay quiet", the answer lights up, a truthful 22 m ring |
| SM-10 | Nightfall | T0 = 18:00:00 | day/night and sleeping camps (M3, M4) | a nightfall tide and one downbeat; camps count their tier in snore rings |
| SM-11 | Hero death | `hero_died` | the death scream and the banner (M2) | a death silhouette per hero, painted out, a soul token that flies home |
| SM-12 | Victory | `match_ended` (the last hall dies) | the end screen | the world holds its breath: the hall caves in at quarter speed under the banner |

Secondary moments, specified but not given a bible sheet: hero summoned at the altar (HER-08), hall tier-up (BLD-20), building cave-in during play (BLD-16), siege shot (CMB-27), loot drop (ITM-01), dawn (world §5.3), research marks (BLD-14).

---

### SM-01. The first command

*Twelve Pavisiers boxed, then a right-click on open grass.* **Anchor:** box release (t = 0), then right-click (t = 600 ms in this example).
**Built from:** UCA-F4, SEL-01, SEL-03, AUD-03, CMB-13, POR-01, HUD-08 (tiles), CMB-08, CMB-10, CMB-01, CMB-03; (P1) CMB-06 order glance, CMB-14 portrait talk, CMB-11 waypoint lines.

| t (ms) | f60 | visual (world) | audio | UI | camera |
|---|---|---|---|---|---|
| 0 | 0 | The selection resolves through `ScreenQuery.box()`, the same function the live preview used, so it cannot disagree. The ring at the drag-start corner starts its pop: scale 0.80→1.06 in 70 ms (`out_quad`), α 0→1 in 60 ms, thickness 1.4×→1.0× over 160 ms. The speaker's ring shimmers (α 1.0, +30 % width) for its line. | The **What** line starts on this frame, 2D on Acks. If the line is debounced (≤ 1 per 400 ms), a selection tick plays instead (tally bundle clack, UI −18 dB). | Unit tiles and bars fill in; the portrait cross-fades to the speaker. | still |
| 0–100 | 0–6 | The speaker's `what` ack: pitch −8° (chin up) in 100 ms, then springs back (ω 12, ζ 0.5). | | | |
| 0–140 | 0–8 | Paint-in front: each ring starts after min(4 ms per 10 px from the drag corner, 140 ms), so the selection spreads from where the hand began. | | | |
| 70→160 | 4→10 | Each ring settles to 1.00 (90 ms `in_out_sine`). | | | |
| ≤ 300 | ≤ 18 | The farthest ring has settled. | | | |
| **600** | **36** | **Right-click.** The move marker spawns on this frame from `ui_time`. Three ripple rings, r 0.25→1.87 m (R = clamp(1 + 0.25·√12, 1, 2.2)), #57E36A with outline #0E2A12, 420 ms `out_cubic`, staggered 70 ms. The pin (a 0.35 m chunky chevron) drops from +0.9 m. **Ripple rank 0** (the unit nearest the click) pulses its ring ×1.0→1.22 in 60 ms, tints it to the order colour, and nods (kingdom: pitch +8° in 50 ms). | The **Yes** line, or, while the What line still speaks, the move tick "tuk" (UI −20 dB, ≤ 1 per 60 ms). | — | still |
| 628 … 908 | 38 … 54 | Ranks 1..11 pulse and nod 28 ms apart (cap 308 ms): a wave you can watch cross the selection. A rank re-nods at most once per 450 ms. | | | |
| ≤ 633 | ≤ 38 | The sim tick applies the order. Paths are requested; the path budget may delay the start 1–3 ticks. | | | |
| 670 / 740 | 40 / 44 | Ripple rings 2 and 3 start. | | | |
| ≈ 700–780 | 42–47 | The first units start: push-off pitch +9° in 90 ms (`out_quad`), then a spring (ω 12, ζ 0.5) to the cruise lean of 4°. Gait hysteresis enters walk only after speed > 0.35 for 80 ms, so separation shoves never flicker the gait. | | | |
| 760 | 46 | The pin lands at +0.15 m (160 ms `out_back(1.6)`), with 3 terrain-coloured dust sprites. | | | |
| 1050 → 1230 | 63 → 74 | The pin holds until 450 ms after the click, then shrinks over 180 ms (`in_back`). The last ripple ring ends at 1160. | | | |
| 1500 | 90 | The column is marching: cruise lean held, breathing desynced, every unit visibly heard you. | | | never moved |

**P0 floor:** ring pop and paint-in, the What/Yes line or tick on the input frame, marker, ripple pulse and nod, push-off. **Spam:** 8 clicks/s gives ≤ 8 live markers, re-clicks within 250 ms and 1.5 m become 200 ms "taps", ≤ 7 nods per unit in 3 s, and no voice spam (combat §7 test 9).

---

### SM-02. The first gold deposit

*A kingdom Hodman returns from the mine to the Moot Hall. The music is at 90 BPM, so a 16th note is 166.7 ms.* **Anchor:** the frame that drains `resource_delivered`.
**Built from:** ECO-03, ECO-04 (+ ★ pre-wind and settle tinkle), ECO-13, ECO-25★, PopupText, MusicClock; (P1) ECO-04 unburdened skip, ECO-30 tachometer.

| t (ms) | f60 | visual (world) | audio | UI | camera |
|---|---|---|---|---|---|
| −300 | −18 | ★**Pre-wind.** The carrying Hodman, whose move goal is this hall, comes within 0.9 m of the footprint. He heaves: torso −12°, arms up, hod raised 0.2 m (120 ms SINE/OUT). This is a prediction: if no delivery comes within 450 ms the hod un-tips (200 ms TIMBER_SNAP) and nothing leaves it. | | | |
| −180 | −11 | The hod ("Agnes") starts to tip about its front lip, 0→40° by the event (QUAD/IN). | | | |
| **0** | **0** | **The deposit.** The hod completes its tip to 55° (80 ms QUAD/IN), the shoulder dips 10° and the torso follows through +8°. The heap sub-mesh hides and a HEAP cut-out (cell 32, 0.22 m) leaves the lip on this frame. The flight solver picks the earliest T in [0.79·T25, 1.34·T25] ≈ 265–490 ms whose landing falls on a 16th note, preferring an 8th: here T = 333 ms. | Wooden hod rattle (World −16 dB). | The gold digits start rolling to the sim value, which is already exact this frame: QUART/OUT over clamp(120 + 6·Δ, 150, 450) = 180 ms. A routine gain never punches or flashes. | still |
| 80 → 240 | 5 → 14 | The hod returns over 160 ms (TIMBER_SNAP, a dry 4.5 % overshoot). | | | |
| **333** | **20** | **Eye and ear meet on the 16th.** The heap drops into the counting hatch (sill 1.9 m, on the wall facing the mine). The hatch shutter flaps inward 25° (70 ms QUAD/OUT, 220 ms TIMBER_SNAP back), and the timber wall flexes within 3 m (≤ 1 per 300 ms). 3–4 COIN spill off the sill along the outward normal ±50° (out 0.6–1.0 m/s, up 1.0–1.8 m/s); they land on the apron top, never inside a wall. Popup "+10" (20 px, GOLD #FFD34D, coin glyph) pops 0.55→1.12 in 90 ms. | Hatch clack + coin jingle (World −10 dB, ≤ 2/s per player). ★**Ledger note:** degree 0 of a kingdom motif (coin-bell timbre) at −16 dB. It is the loudest ledger note of the match; habituation starts here (−1.5 dB per minute, floor −26). | (P1) the HUD coin icon turns with income | |
| 423 → 533 | 25 → 32 | The popup settles to 1.0 (110 ms SINE/IN_OUT) and starts rising 40 px. | | | |
| 450–700 | 27–42 | (P1) Unburdened skip: the first 2 strides bob ×1.35, lean −3°, and the straw hat kicks 4°. | | | |
| ≈ 780 | ≈ 47 | First coin contact on the apron, one bounce (e 0.25; the bounce also damps horizontal velocity, so coins never skate). | | | |
| ≈ 980 | ≈ 59 | The coins lie flat and run COIN_SETTLE: 25° tilt, precession rising 4→11 Hz over 150–250 ms, like a real coin. | | | |
| ≈ 1180 | ≈ 71 | The first coin is at rest, and stays still ≥ 300 ms. | ★Settle tinkle: 3 ticks 90 / 60 / 40 ms apart, scheduled at its rest time. | | |
| 933 → 1333 | 56 → 80 | The popup fades from 0.6·D and is gone at 1 s. | | | |
| ≈ 1480 → 1900 | ≈ 89 → 114 | The coins erode (the alpha-scissor threshold rises 0→0.85) over the last 25 % of their life, never shrinking or popping. | | | never moved |

**P0 floor:** the tip, the flight landing on a 16th, the hatch, coins with SETTLE, the popup, the jingle, the exact counter. **Clans variant:** the Yurtwright swings the felt bag into both hands (200 ms FELT_BOB), and a 10° bow whose down-stroke lasts 160–340 ms is chosen so the bag touches the felt flap's sill (1.2 m) on a 16th. The flap lifts 20° and draws the bag in; 2 coins tumble out; a felt thup + bag clink. There is no toss, because the Tormai are courteous (ECO-04).

---

### SM-03. Tree felled

*A Hodman fells an oak; 0.8 s chop cycle.* **Anchor:** the felling strike's contact (the wrap of `work_progress`): the tick of the last `tree_harvested` (left = 0), which also emits `tree_toppled`.
**Built from:** ECO-08, ECO-09, ECO-10★, ECO-11, ECO-20★, Stumps; (P1) ECO-11 logs and leaf litter, ECO-19 (P2) chop notch.
**Pre-roll:** on earlier chops the tok stepped down the pentatonic, degree 0 above 66 % lumber left, 1 above 33 %, 2 below, and the trunk leaned up to 6° away from the chopper (ECO-10★). By now the tree sounds hollow, in key.

| t (ms) | f60 | visual (world) | audio | UI | camera |
|---|---|---|---|---|---|
| −480 | −29 | The last wind-up: the axe travels back to the top (cycle 0.40→0.80, QUAD/OUT, body pitched back 10°). | | | |
| −160 | −10 | **Hang** at the top for ≈ 90 ms (cycle 0.80→0.91): you can see the axe load. | | | |
| −72 | −4 | The strike (CUBIC/IN). | | | |
| **0** | **0** | **Contact.** A 90 ms *visual* hold on the contact pose (the felling strike; normal chops hold 70 ms); the sim keeps running and the hold is taken out of the recoil. 3–5 bark/inner chips (60/40 %) fly in a 70° cone away from the worker. The FallingTreePool takes over the instance on this frame (copying transform and tint; the 2 nearest the focus keep their shadows), the MultiMesh instance hides, and the stump appears beneath. **Fall direction:** 8 compass directions are scored: ≥ 3 m clear, +2 if within 60° of `away`, **−3 if facing the camera**, so trees never fall onto your view. | The tok on degree 2 (the hollowest) + the creak layer at −10 dB relative (World −12 dB). | — | still |
| 0–180 | 0–11 | **Hesitation:** the trunk tips to 4° (SINE/OUT). ★**"Timber!" beat:** the chopper steps back 0.2 m, leans back 10° and looks up (head pitch −20°); own workers within 4 m of the fall line flinch (sy 0.92, 6° away, 200 ms). | Creak (World −14 dB). ★"Hup!" (kingdom) / "Hai!" (clans), World −16 dB, ≤ 1 per 10 s per player. | | |
| 180 | 11 | The fall: angle = 4° + 86°·((t − 180)/900)^2.2 about a pivot 0.15 m off the base. It accelerates like dead weight, ≈ 25° at 650 ms, ≈ 57° at 900 ms. | | | |
| ≈ 650–1080 | ≈ 39–65 | | Whoosh (World −16 dB) through the fast half. | | |
| **1080** | **65** | **Impact** at 90°: a bounce 90→84→90° (220 ms TIMBER_SNAP); 14 LEAF along the canopy line (flutter, 1.6–2.4 s); 10 low DUST_PUFF (s 0.6 m) along the trunk, skipping points within 0.8 m of a unit. | Leafy crash + thud (World −8 dB, priority 40). | | **no shake** (trees are not on the whitelist) |
| 1300 | 78 | (P1) The trunk is replaced by 3 log segments that roll ≤ 0.4 m downhill and stop within 500 ms; (P1) a leaf-litter patch (α 0.6→0 over 30 s); a sawdust ring at the stump (α 0.4, 20 s). | | | |
| 1500 | 90 | The worker walks to the next tree on the sim's schedule. The stump is permanent (world memory); the trunk erodes at 6 s. | | | |

**P0 floor:** the hang and hold, chips, the hollow tok, the "Timber!" look-up, the scored fall, impact leaves and dust, the stump. **No valid direction:** the trunk telescopes into the stump (600 ms, Y 1→0.15) with 14 leaves and a creak-crunch.

---

### SM-04. The first building completed

*A kingdom Drill Yard (8 × 8 cells, r_h 2.83 m), 1 Hodman + 2 hod carriers (Hod Chain), 90 BPM, so the grid step is 667 ms.* **Anchor:** the completion tick (`building_completed`). Rows before 0 are the anticipation, driven by the predictor t_done = (1 − p) / `build_rate()`, re-evaluated every frame.
**Built from:** BLD-06, BLD-07K, BLD-08, BLD-24, BLD-09, BLD-11 (Drill Yard dummy), MusicClock; (P1) BLD-24 topping-out, BLD-26 admire beat, BLD-09 unlock light-catch.
**Pre-roll:** every strike laid a 0.35 m course (BLD-06), stone to 1.2 m then timber; rafters rose at 50 % and the bare pole at 75 %; the pennant-mast crown, staged on the apron from the start, was hoisted at 82–90 % and seated at 93 % with a stone-thud clunk.

| t (ms) | f60 | visual (world) | audio | UI | camera |
|---|---|---|---|---|---|
| −1600 | −96 | (P1) Topping-out: a linden sprig is hoisted up a rope to the ridge (600 ms); the builders look up (head −20°, 400 ms). | (P1) "Hoo!" (World −14 dB) | | |
| −1200 | −72 | **Accelerando:** the site's strikes leave the grid and warp from 1.0× to 1.5× tempo over 600 ms; the fresh-plaster edge band (#FFE2A8 ×1.3) ramps its energy 1.3→2.2 (QUAD/IN). | Scaffold creak (World −16 dB); strikes keep their material timbre (mallet tok + chips on timber courses). | | |
| −510 | −31 | **Shared wind-up:** every builder raises its tool to 120° over 450 ms (SINE/OUT) and hangs; both carriers lift their hods overhead. | The construction bed starts its 400 ms fade. | | |
| −60 | −4 | The strike (60 ms CUBIC/IN). | | | |
| **0** | **0** | **The final blow lands on the completion tick.** If the event is late, the contact pose holds (≤ 150 ms); if the prediction missed by > 150 ms, the wind-up aborted and this row plays on the event alone. The last strip closes (P→1 over 80 ms); the edge flashes ×2.5 (latched). Scaffold collapse: the ledgers drop 0.28 m (0–150 ms, JUICE_G). Timber SETTLE: Y 1→1.03 (90 ms QUAD/OUT), XZ = 1/√Y. | Timber clatter (World −8 dB). Owner: the kingdom complete cue, a hand-planed wood stroke (UI −6 dB, 1.2–1.5 s; a 0.6 s variant for the same def within 20 s). | Newly enabled card buttons appear; off-screen, the advisor line and a clickable feed line play. **No minimap ping** (completions never ping). | still |
| ≤ 100 | ≤ 6 | The shared material is restored. The building has been usable since 0. | | | |
| 100–450 | 6–27 | The 8 poles topple outward 80° about their bases (QUAD/IN). | | | |
| 150–750 | 9–45 | The team banner is hoisted (`banner_raise` 0.15→1, SINE/IN_OUT rope pull). | | | |
| 200–600 | 12–36 | The windows ramp on at night (#F08A2A HDR 1.4), or show a 15 % inner glow by day. | | | |
| 310 | 19 | SETTLE ends (220 ms TIMBER_SNAP: a dry 3 % snap; stone buildings drop 2 cm instead, felt breathes). | | | |
| **450** | **27** | **Dust "fwump":** the poles land. 17 DUST_PUFF (clamp(round(6·r_h), 8, 22)) along the scaffold line, out 1.5 m/s, end size min(0.6·r_h, 1.4 m) = 1.4 m, ≤ 0.8 m high, α 0.45, 700 ms, skipping points within 0.8 m of a unit, so the builder at the wall is never covered. | "Fwump" (World −6 dB), the kingdom's completion signature. The builder's job-done line (Acks) starts **after** the fwump: *bible staging*, rule 9, so cue, clatter and voice do not land on one frame. | (P1) Light catch on the unlocked buttons (450 ms ×2, 300 ms apart). | |
| 450–1150 | 27–69 | (P1) Admire beat: the builder steps back 0.2 m, looks up 15° and dusts off its hands (two claps at 4 Hz). Any order cancels it at once (80 ms). | | | |
| 500–900 | 30–54 | The scaffold pieces erode (alpha scissor). | | | |
| 750–2250 | 45–135 | The banner flutters (CLOTH ×2.2, decaying to ×1). | | | |
| 1500 | 90 | The yard stands still until it trains; then the straw dummy is thwacked every 2 grid steps (BLD-11). | | | never moved |

**P0 floor:** the accelerando, the shared wind-up landing on the tick, the edge flash, settle, scaffold collapse with fwump, banner, cues. **Clans variant (BLD-07C):** the builder's wind-up targets the gong staged at the door. The completion strike is a gong strike (World −6 dB) with BRONZE_RING (ω 28, ζ 0.12, ≥ 3 visible oscillations in time with the ring-out). The dome breathes (FELT_BOB), and 8 ochre felt-fluff puffs rise from the smoke-ring.

---

### SM-05. First contact and the first fall

*Tormai Grapplers (mace, blunt, mass 1.8) charge a Pavisier line (falchion; metal body with a wood pavise on the ±60° frontal arc; mass 1.2). Example damage point dp = 0.5 s (the data default for melee soldiers).*
**Part A anchor:** the first melee damage tick with no melee hit within 6 m in the previous 4 s (★CMB-36).
**Built from:** CMB-16, CMB-17, CMB-18, CMB-20, CMB-21, CMB-29, CMB-36★, AUD-02; (P1) CMB-38 engage grammar, WLD-24 battle silence, AUD-02 battle bed.

| t (ms) | f60 | visual (world) | audio | UI | camera |
|---|---|---|---|---|---|
| −500 | −30 | The wind-up starts. (P1) Tormai engage grammar: the Grappler **bows** +12° across u 0→0.35 of the wind-up ("they apologise before hitting you"); (P1) the Pavisier taps his pavise rim forward twice. The mace loads to pose −0.45 over the first 72 % (`out_quad`). | (P1) the Pavisier's "tok-tok" (`hit_wood_l` −14 dB) | | |
| −140 | −8 | Full load (u = 0.72). The snap starts (`in_cubic`). | `sw_blunt` starts at contact − `peak_ms`, so its peak lands on contact. | | |
| −75 | −5 | The smear reveal starts (u = 0.85): a 60° overhead dry-brush stroke, beginning outside the attacker's hull, sweeping head→tail over 0.15·dp = 75 ms, so the stroke head reaches the mace tip at contact. | | | |
| **0** | **0** | **Contact = the damage tick** (pose P = 1 exactly). A 60 ms visual hold on the attacker. Victim rim flash latched at its peak (#FFF6EC; albedo × 0.4; ≤ 0.95 linear). The origin is inside the frontal arc, so the material is the pavise's wood: 5 splinters (#8B5A2B/#B07A45, 0.08 m, spinning 8–12 rad/s) + a sawdust puff; blunt adds a ground dust ring (r 0.2→0.8 m, 150 ms). ★**Clash:** sparks ×1.3 and a dust ring (r 0.3→1.2 m, 220 ms, α 0.45). | `hit_wood_h` (Combat −4 dB; the attacker is ≥ 1.5 mass, so the heavy set) + ★the clash layer `hit_metal_h` + `hit_wood_l` at +2 dB; a pain vocal on 20 % of hits (`hash01`). `Vfx.battle_started(pos)` fires. | The lost bar segment turns ghost #FFE3A0; the border flashes white for 70 ms (latched). | **no shake** (melee never shakes) |
| 0–90 | 0–5 | Knockback: A = 0.11 m × clamp(0.6 + dmg/(0.08·max_hp), 0.6, 1.6) / 1.2, through the Pavisier's spring (ω 21.9, ζ 0.52), tilting 1.2 rad/m about the feet; plus 90 ms of ±0.035 m tremble (`vnoise`, 20 Hz). Ring and bar stay on the sim position. | (P1) The ambience ducks −5 dB over 500 ms (battle silence); the battle bed may begin. | | |
| 30–80 | 2–5 | The flash falls to 0 (`out_quad`) as its tint warms to #FF5A48. | | | |
| 55 | 3 | Knockback peak (the first rebound will be 15 %). | | | |
| 60 | 4 | The attacker's hold ends; recovery = 1 − `out_back(r, 1.6)`. | | | |
| 297 | 18 | The Pavisier has settled. Mass is felt: a heavy rings slower and rebounds less. | | | |
| 400 | 24 | The splinters are gone (≤ 400 ms life: effects never outlive their information). | | The ghost holds for 400 ms after the latest hit, then drains (`damp` 7/s, ≥ 0.25 bar/s). | |

**Part B anchor:** the killing blow on the first Pavisier (`hit_landed` with KILL). **Built from:** CMB-30, CMB-31; (P1) CMB-42 bar shatter, CMB-30 hat pop, CMB-35 kill-confirm and kill styles.

| t (ms) | f60 | visual (world) | audio | UI | camera |
|---|---|---|---|---|---|
| **0** | **0** | **Death beat:** the pose freezes in its hit reaction and the flash holds at 1.0 white for 60 ms. The ring and bar vanish this frame; (P1) the bar breaks into its 3 thirds, which fall 20 px with a ±12° twist over 150 ms, pinpointing the death inside the blob. | **Kill thock:** the impact's heavy variant at +3 dB, pitch ×0.95, its 250 ms tail never cut by spacing; death vocal (−6 dB). | | |
| 60 | 4 | Topple A (60 % by `hash01`) **away from the killing hit's origin** (±20° yaw): pitch 0→90° by 560 ms (`in_quad`), sliding 0.15 m. Topple B (40 %) spins ±40° while falling. Clip units seek the death branch so its contact lands at 560 ms. (P1) Hat pop, 30 % of the time and always on overkill: the kettle hat leaves the head (up 1.6 m/s, away 1.2, spin 8 rad/s). | | | |
| 200–300 | 12–18 | The falchion and the pavise detach, bounce once (e 0.3) and settle at ≈ 20°; the pavise falls face-up, its painted wheel showing. | | | |
| 250 | 15 | (P1) The killer's kill style, at its backswing end: a Grappler hip-throws a victim of mass ≤ 1.5 over and past himself, otherwise bows 12° over the fallen. | | | |
| **560** | **34** | **Body contact:** a ring of 6 terrain-coloured dust sprites at the hip; the contact blob stretches 1.6× along the fall. | `fall_armoured` (−6 dB, pitch 1.1 − 0.1·mass = 0.98). | | |
| 640 → 760 | 38 → 46 | A 7° bounce back (80 ms `out_quad`), then settle (120 ms). | | | |
| **700** | **42** | ★**The flag is lowered:** `team_sat` 1→0.2 sweeping feet→head over 1.4 s (soft 0.15 m front), value ×0.85. From here on, a corpse never reads as a live unit. | | | |
| 760–1460 | 46–88 | (P1) The hat rolls on its rim along a 0.6 m arc (700 ms) with a growing wobble and falls flat. | (P1) a clank | | |
| 1500 | 90 | The ebb is 57 % done. Later: dissolve into faction remains at 3.6–5.6 s (P1), sink at 6.5–8.0 s (P0), a stain in the scar map (P1). | | | never moved |

**P0 floor:** contact on the tick with hit-stop, rim flash, material splinters, smear, mass-scaled knockback, bar ghost, death beat, styled topple with contact dust, the ebb and the sink.

---

### SM-06. Camp cleared

*The Wheel Marshal and a kingdom squad kill the last creep of an awake Sootcoat camp.* **Anchor:** the last kill's tick; `bounty_awarded` and `camp_cleared` arrive in that same tick.
**Built from:** CMB-28 (bounty), CMB-30, CRP-04, HER-03 (HUD pour + ★XP particles), HER-01; (P1) CRP-04 dressing topple, settling dust and coin burst, HER-02 post-fight exhale, CMB-43, WLD-24.

| t (ms) | f60 | visual (world) | audio | UI | camera |
|---|---|---|---|---|---|
| **0** | **0** | The death beat and topple; the soot victim throws a black puff (#2A2622). Bounty "+N" (PopupText, #FFD34D, 20 px, coin glyph). **Summary stamp** at the camp centre + 2.4 m: "+46" with the coin glyph (24 px) over "+180" with the XP glyph (20 px, #FFE9A8). It starts at the sum of the camp's already-expired bounties and stamps 1.6→1.0 in 120 ms (`in_quad`). ★XP: n = clamp(round(xp/15), 1, 6) **ivory spoke-chips** launch from the kill point at 1.0 m, 25 ms apart, and burst 0.4 m out and up (100 ms `out_quad`). | Kill thock + death vocal. **Camp stinger** (kingdom: a hand-bell, a rising horn third and a snare tap; 1.6 s, 2D UI −8 dB, the clearing player only; never the level-up motif). | The XP bar pours its new segment (#FFF6DE, 300 ms `out_quad`, cooling to #E8B84A over 600 ms). | still |
| 0–300 | 0–18 | **The merge:** every live bounty "+N" of this camp (≤ 1.2 s old, including the one just born) flies into the stamp (300 ms `in_cubic`), and the stamp's digits roll up as each lands (a 1.12 bump over 60 ms). The final number is the camp's total. | | | |
| 100–180 | 6–11 | ★The chips **hang** for 80 ms and turn their points toward their hero. | | | |
| 180–520 | 11–31 | ★They home on the hero's chest along a Bézier (control point +1 m, `in_cubic`, 220–340 ms by hash), stretching ×2.2 along their velocity. | | | |
| ≈ 350–645 | ≈ 21–39 | ★Each chip clicks into the wheel sigil (20 ms snap); the band pulses (r 0.9→1.15 m, 100 ms, latched); the XP arc eases to the new ratio. | Dry ivory clicks (UI −26 dB, the selected own hero only, ≤ 4/s), pitched up the current scale as the next level nears (`pitch_locked`). | | |
| 0–620 | 0–37 | (P1) The camp's standard topples 80° (500 ms `in_quad`) and bounces back 8° (120 ms `out_quad`), with dust on contact; the campfire puffs one smoke ring and goes out. | (P1) the fire loop stops | | |
| 0–900 | 0–54 | (P1) 20 settling-dust puffs rise 0.8 m from inside the camp bounds: "this ground is safe". Vertical, never a ring. | | | |
| ≤ 750 | ≤ 45 | XP ceremony complete (asserted). | | | |
| 600–1500 | 36–90 | (P1) The Marshal's post-fight exhale, 0.6–1.5 s after the clear (hashed): she taps three spokes of her wheel-shield with the war-pick, 250 ms apart. | (P1) "tik" ×3 (World −24 dB) | | |
| 1520 | 91 | The stamp hold ends, then RISE_FADE. | | The minimap shield pip shows the camp cleared. | |
| 1600 | 96 | | The stinger ends. | | never moved |

**P0 floor:** the stinger, the stamp swallowing its bounties, the bounty popups, the HUD pour, and (★) the XP chips. Later beats (P1): survivors lower their weapons in a wave at quiet + 3 s (CMB-43), and one bird calls from the clearing at quiet + 3.5 s (WLD-24).

---

### SM-07. Hero level-up

*The Wheel Marshal (kingdom) reaches level 3 from a level-crossing kill.* **Anchor:** `hero_level_up(u, 3, 1)`, emitted in the same tick as, and after, `hero_xp_gained(…, levels_crossed = 1)`.
**Built from:** HER-04, HER-01, HER-03 (HUD wrap + ★particles), HER-05 (skill pip), AUD-01; (P1) HER-04 pillar, light and wear, NTF-04 ribbon.

| t (ms) | f60 | visual (world) | audio | UI | camera |
|---|---|---|---|---|---|
| **0** | **0** | **Wind-up:** the ground sigil contracts to r × 0.9 and dims to value 0.6 (70 ms `in_quad`), a visible inhale before the payoff. ★The level-crossing XP chips spawn now and fly **direct in 180 ms** (`in_cubic`), so the cause arrives inside the wind-up. HP and mana bars widen to the new max with a 400 ms gold border flash (bit 2): exact on this frame. | **Signature cue** (a harp run + a choir "ah" on an open fifth with no third, so it sits over any mode; 1.4 s, rendered on D): 2D for the owner and allies (Alerts −4 dB, priority 100), 3D −8 dB for others. (P1) Music ducks −5 dB for 1.4 s. | The XP bar pours to 100 % (200 ms `out_quad`). | **never shakes** |
| 60 | 4 | (P1) The far-zoom pillar fades in over 80 ms: a fresnel tube r 0.4 m, 7 m tall, its HDR 2.0 core starting above h + 0.3 m so it never washes over the hero. | | | |
| 70 | 4 | **Level pose `chin_rap`:** chin up −12° (120 ms `in_cubic`). **The standing emblem** (a copy of her sigil face, r 1.05→0.8 m, centre 0.05→1.3 m up and 0.35 m behind her) **stands to face the camera**: pitch 0→40°, settling at 90° − abs(camera pitch) = 34° (`out_back(1.6)`, 180 ms), so it reads as a circle (aspect ≥ 0.9, ≈ 74 px), not a squashed ellipse. Units behind it show through its α ≤ 0.3 face. | | | |
| ≤ 180 | ≤ 11 | The first chip clicks home, and the ground band flares to HDR 2.2 (settling over 900 ms). | ivory click | | |
| 190 / 300 | 11 / 18 | She raps the shield rim twice with the war-pick haft, 110 ms apart. | "tunk" ×2 (World −18 dB) | | |
| 200 | 12 | | | **XP wrap:** an 80 ms white flash at 100 %; the level badge starts its coin-flip (scale.x 1→0 in 140 ms `in_quad`); a light catch sweeps the portrait frame (400 ms); the 3D portrait gets a vertical light wipe (500 ms). | |
| **250** | **15** | **The ratchet:** one 36° snap (50 ms `in_cubic`, one segment of ten), a 4° recoil (`out_back(2.0)`, 40 ms) and a 30 ms hold. The new 3rd segment arrives at 12 o'clock and lights 30→100 % with a 1.0→1.15→1.0 pop. The hub flame flares HDR 2.2→1.0 over 600 ms. 18 bronze sparks fly off the pawl point (reserved sprite range; up 2–4 m/s, 700–900 ms). **Numeral:** the faction badge (46 px) + "3" (34 px, #FFE6A0, ink outline) + an up-chevron stamp in from 1.5× (60 ms `in_cubic`, 4 % recoil over 50 ms). No words, so nothing to localise or to echo WC3. (P1) A LightBudget priority-4 light (#FFD9A0, energy 3→0 over 900 ms). | Pawl clack (World −12 dB, 3D) | | |
| 280 | 17 | | | The bar snaps to 0 with a 4 px shine and pours the remainder (300 ms). | |
| 340 | 20 | | | The badge swaps to "3" and flips back (140 ms `out_back`); the "+1" skill pip POP_INs on the hero button and bobs ±3 px on the ambient clock. | |
| 380 | 23 | (P1) The pillar's hold ends (an enemy hero's is capped at 250 ms in Busy/Brawl). | | | |
| 470 | 28 | Chin lowered (160 ms). | | | |
| **700 → 820** | **42 → 49** | **The emblem slams flat** back into the ground sigil (pitch → 0°, `in_cubic`). | | | |
| **820** | **49** | **Contact:** the hero dips (sy 0.97 for 40 ms); a soft, **edgeless** dust ring runs r 0.6→1.6 m (α 0.35→0, 400 ms) with 6 soft puffs; the band holds HDR 1.6, then decays to ≤ 1.0 over 600 ms. (P1) **Wear:** a new brass stud appears on her shield rim (a 50 ms snap to 1.4× value, 60 ms recoil). | **Level ladder** ★ (our twist): the cue's final bell, a separate stem, rings `MusicClock.note(1)` of the current track's pentatonic (L2..L10 = note(0)..note(8)). It is recorded at C and transposed deterministically (`pitch_locked`), so the climb never clashes with the score. | | |
| 1100 | 66 | (P1) The pillar is gone; the numeral rises 40 px and fades by 1500. | The cue tail ducks −6 dB. | | |
| **1150** | **69** | | **The level-up line** `levelup_a` (Acks; 3 takes, never the same twice in a row; at L5 `levelup_5`, L6 `levelup_6` "ultimate unlocked", L10 `levelup_10`). | | |
| 1400 | 84 | The band is back at emission ≤ 1.0. | The cue ends. | | |
| 1500 | 90 | Done: 1.5 s, no frame of control taken away. | | | never moved |

**P0 floor:** wind-up, level pose, standing emblem with ratchet, numeral, slam with dust, cue, ladder bell, line, bar wrap and badge flip, chips. **Tormai variant (the gong):** at 250 ms the gong emblem is **struck** by the hero's weapon prop (a 33 ms impact frame at the boss, 1.25× scale, HDR +0.5). Three standing-wave ripples cross its face 140 ms apart (r 0.1→0.75 m over 420 ms each), the band wobbles ±0.06 m at 7 Hz with e^(−t/0.25 s), and the new segment *swells* in (300 ms `in_out_sine`). For the Uncut (`no_rotation`) the emblem is born at the camera-facing tilt and rises straight up. **L6:** the ult gem locks in at 820 ms and a low brass swell sits under the whole cue. **Multi-level:** one ratchet or strike per level, with the bells arpeggiating up the ladder.

---

### SM-08. The ultimate: the Wagon Ring

*The Wheel Marshal casts the Wagon Ring (175 mana, 11 m, 7 s; cast point 0.5 s). Allied non-structure units inside at cast cannot drop below 1 HP for 7 s, wherever they go.* **Anchor:** `ability_released` (the tick the sim protects them). Rows before 0 run on `FxRead.cast_progress()` c, which is exactly 1.0 on the release frame and < 1 before it, even across a pause.
**Built from:** ULT-01, ULT-02 (+ ★rise wave), ABL-01, HER-01 (cast mode, lock mode), STS-01 (`LOCK_RIM`), CAM-05★, HVF-1; (P1) ULT-01 ducks and `Atmos.shock`, ULT-02 sky-wheel clicks and the "saved ×N" stamp.

| t (ms) | f60 | visual (world) | audio | UI | camera |
|---|---|---|---|---|---|
| **−500** | **−30** | `ability_cast_started` (she has turned to face): her sigil's six spokes morph into the school glyph (90 ms `in_cubic` snap; kingdom clockwork). She plants her feet (sy 0.95 over the first 30 % of c). An ivory chalk **capture ring** starts growing from her sigil toward **exactly 11 m** (edge strip α 0→0.6 over the cast point): the honest preview of who will be caught. | **Ultimate stinger:** owner 2D (Alerts −6 dB, priority 95); anyone who can see her hears it in 3D at −4 dB, an honest warning. (P1) Music ducks −4 dB for 1.5 s. | **ULT-01 frame:** the vignette fades in over the cast point to α 0.14 in ember-ivory #FFC46B, only outside 55 % of the screen radius, with a painted dry-brush edge; the console's brass trim lights in the same colour (LDR). | still |
| −350 | −21 | She raises the wheel-shield overhead (pitch −20°, +0.1 m, `out_quad`). | | | |
| −333 | −20 | Glyph **click 1** (20°, a 40 ms `in_cubic` snap + 3° recoil). | | | |
| −250 | −15 | Dialect burst 1: 5 bronze sparks off the shield hub (0.05 m, HDR 1.8, 300 ms). | | | |
| −167 | −10 | Glyph **click 2**. | The school riser starts at c ≥ 1 − peak_s / 0.5, so its peak lands on the release. | | |
| −120 | −7 | | (P1) The Combat bus dips −3 dB: a small hole for the release to land in. | | |
| **0** | **0** | **Release.** Glyph **click 3 = the lock** (a 1.25× punch and a value pop, no HDR; it morphs back to the face over 250 ms). A 110 ms ultimate hold with an impact frame. Dialect burst 2. The capture edge snaps to α 0.85 (smooth ivory, an own effect) with an ivory wash fill at α 0.12. ★**Wheel 1** (at her facing) snaps up out of the ground: a ghost wagon wheel Ø 1.6 m, rim and 6 spokes only (ivory, rim #FFB46B at HDR 1.6), empty between the spokes so units behind show through; a 60 ms `in_cubic` snap and a 4° recoil (`out_back(2.0)`, 40 ms). LightBudget priority 5 (ground glow on Compatibility). | **The hero calls her shot:** the ultimate shout (Acks, priority 95; 2D owner, 3D −6 dB for others). A wooden thump. A rolling-wheel rumble starts (3D −10 dB, until 850 ms). The Combat dip restores. | | ★**Trauma +0.40** on the ability channel (own slam ultimate, within 8/20 m of the focus, visible only): a directional kick of ≈ 8 px away from the ring centre plus ≈ 6 px of 14 Hz noise, gone by 250 ms. (P1) `Atmos.shock` 0.8: the grass flattens outward and the trees flinch. |
| 20 … 120 | 1 … 7 | ★**The wheels rise as a wave:** the pairs at ±30°, ±60° … stand up 20 ms apart, her back last, and twelve thumps clatter round the ring. | thumps ×11 | | |
| 110 | 7 | Her hold ends; follow-through. | | | |
| 220 | 13 | All 12 wheels stand on the circumference, upright and tangent. | | | |
| **250–850** | **15–51** | **The roll call ★:** every wheel rolls one 30° sector round the centre in 600 ms (`in_out_sine`; ω = v / r, so they truly roll; the spokes swap to their painted spin-disc frame while the pattern exceeds 7.5 Hz). **As a wheel passes a captured unit's bearing, that unit is called:** it gets its **iron lock rim** (feet layer `LOCK_RIM` at its ring radius in IRON_RIM #5A5048, with a padlock pip at screen-down; heroes get the sigil's lock mode) with a 60 ms snap. Together the wheels sweep 360°, so every captured unit is called within 600 ms. Units outside at cast, enemies and structures get nothing. | A soft clink per called unit (−22 dB, ≤ 8/s). | | |
| 600 | 36 | | | The tint's hold ends; it fades out over 1200 ms. | |
| **850–1250** | **51–75** | **The hand-off:** the capture edge and fill are painted out through the brush mask (400 ms `in_quad`); each wheel **collapses onto the centroid of its sector's captured units** (400 ms `in_cubic`, Ø 1.6→0.5 m) and splits into their lock rims, each brightening once (100 ms). A sector with nobody in it: its wheel topples flat (380 ms) into ivory dust. | A low chain-rattle loop at the Marshal (3D −18 dB) for the 7 s. | | |
| 1250 | 75 | **The truth now rides on the units, not the ground:** an ally who walks in has no rim and is not protected; a captured unit that walks away keeps its rim. | | | |
| 1500 | 90 | The lock rims drain clockwise as (t_end − `sim_time`) / 7 s (the padlock blinks at 2 Hz in the last second). (P1) The sky wheel stands at h + 1.2 m over her, facing the camera, turning 0.25 rev/s, α 0.5→0.25 over the 7 s, fading to 0.2 while it overlaps any unit's health-bar anchor. | | | |

**Afterwards:**
- **Lethal block ★** (`lethal_prevented`): the unit's lock rim rings like struck iron (emission 1.0 for 120 ms, a 1.0→1.12→1.0 recoil) and throws 8 bronze sparks; the sky wheel clicks one 20° notch; the health bar shows an iron lock notch; a clang plays (Spells −8 dB, ≤ 4/s).
- **End at 7 s:** the padlocks spring open (a 120 ms shackle pop, chained 30 ms apart), the rims fall apart into ivory spoke-chips, and each unit's +15 % heal shows as a rising gold-green flash.
- (P1) A "saved ×N" stamp with a bell for the owner.

**P0 floor:** cast mode, capture ring, frame, stinger, shout, hold, ★rise wave, roll call, hand-off, lock rims, lethal block, ★trauma.

---

### SM-09. Base under attack, and the horn

*The camera is with the army, 80 m away, when a raider hits a Hodman at the west mine.* **Part A anchor:** the first `unit_damaged` on an own worker off-screen.
**Built from:** NTF-01, NTF-02, NTF-03, CAM-04, AUD-01, AUD-04, ECO-27★, UCA-F5; (P1) NTF-01 compass, CAM-04 ink veil, arrival ripple and return crumb.

| t (ms) | f60 | visual (world) | audio | UI | camera |
|---|---|---|---|---|---|
| **0** | **0** | (Off screen, drawn only for whoever sees it.) ★The Hodmen within 6 m flinch (sy 0.94 for 120 ms) and turn toward the raider; their work goes on to the sim's schedule. | **Faction alarm**, dissonant and falling, sounding like nothing good: kingdom = two cheap tower bells a tritone apart, 5 strikes 110 ms apart, ≈ 740 ms; clans = a slit drum. AlarmPan → Alerts −6 dB, **panned 0.4 × x toward the alert**, so the ear says "left" before the eye finds anything. The raid's own combat sounds are culled (beyond 50 m × d/28). | **Minimap ping:** 3 rings, workers kind, with a pick pip. **Feed line** "Workers harried · west mine" with a [Space] chip slides in (kingdom slip: 40 px→0 in 220 ms `out_quart`, α 0→1 in 120 ms). ★**The answer lights up:** the hall's **Levy Horn** button pulses on the urgent clock (2 Hz, border #FFB347 α 0.4↔1.0), and the hall's portrait frame ticks once (UI −16 dB). | still |
| 220 | 13 | | A brass tack tick (UI −22 dB) | The tack pins the feed slip (latched squash). | |
| **350** | **21** | | **Advisor** (Alerts): "They're at the Hodmen! Shall I sound the horn?" The Voice sidechain dips Music and Ambience 4–6 dB (no explicit duck). Lines older than 2.5 s would have been dropped as stale. | | |
| **600** | **36** | | | The player presses **Space** (example time). | **Glide** to the newest cluster: T = 150 + 55·log2(1 + D/12) ≈ 312 ms for 80 m, `out_quart`, so half the trip is done in the first ≈ 50 ms. Distance and pitch are unchanged. (P1) Ink veil: α 0.28·(1 − u)³, outside 45 % of the radius, with a page whoosh (UI −22 dB). (P1) The pre-jump view is pushed as a return crumb (Shift+Space). |
| 740 | 44 | | The alarm ends. The category is now throttled for 8 s. | | |
| **912** | **55** | The raid is on screen: rim flashes, splinters and the flinching line. | The listener moved with the focus; the fight's sounds now play on Combat, unmuffled (AUD-04). | (P1) Arrival ripple: a red notched ring r 0.5→3.0 m in 600 ms at the alert. | arrived |
| 1200 | 72 | | | The player selects the hall and presses the Levy Horn hotkey (example time): Part B. | |

**Part B anchor:** Levy Horn key-down (HUD-01: the card acts on the down-stroke). **Built from:** HUD-01, ECO-21, the terrain ring list, FND-6 (flail); (P1) ECO-21 levy flag and per-levy timer sliver.

| t (ms) | f60 | visual (world) | audio | UI | camera |
|---|---|---|---|---|---|
| **0** | **0** | | Button click: wood knock + iron latch tick (UI −12 dB). | Press (45 ms `out_quad`: y +2 px, scale 0.96, icon ×0.82) and a hotkey echo on the slot; the urgent pulse stops (the answer was used). | |
| ≤ 33 | ≤ 2 | `levy_called(hall)`: the **truthful ring**, the hall footprint dilated by **exactly 22 m** (the sim's `edge_distance` test, drawn by the terrain shader so it drapes over cliffs), its front growing over 700 ms (CUBIC/OUT); a LEVY ivory #EDE2C8 line with 6 burgundy #7B1E2E notches. Arming starts for every Hodman inside (1.5 s, timed from this tick): 0–300 ms the tool is thrust into the back strap and the hod swings onto the back, **its gold kept** (TIMBER_SNAP). | **Levy Horn:** a two-note low wooden horn (owner 2D, Alerts −4 dB, priority 95; 3D −6 dB for others who see the hall). | | |
| 45–110 | 3–7 | | | Brass latch release: scale 1.04 at 60 ms, 1.00 at 110 ms, brightness ×1.18 for 70 ms. | |
| 250–700 | 15–42 | The straw hat flips back onto its chin cord (CLOTH); the kettle hat comes off the belt onto the head (a 0.35 m arc, 220 ms) and settles (sy 0.94, 100 ms). As the ring's front reaches each Hodman, at its own edge distance, he turns his head to the hall and nods (120 ms). | A clank per hat. | | |
| 700 | 42 | The ring holds at exactly 22 m for 400 ms. (P1) The burgundy levy flag reaches the top of the hall's second pole (600 ms rope hoist + CLOTH flick). | | | |
| 700–1350 | 42–81 | The flail unslings from the back and swings once overhead (the FND-6 flail head). | Chain rattle (−14 dB). | | |
| 1100–1600 | 66–96 | The ring fades out over 500 ms. A ring always means reach; ceremonies never draw rings. | | | |
| **1350–1500** | **81–90** | **Stamp** (sy 0.94→1.03→1, STONE_THUD): the militia stands armed. Nothing is left on the ground and nothing flies back across the map. | One "Ready" bark per levy group (Acks). | (P1) A 2 px ivory timer sliver under each levy's HP bar. | |

**P0 floor:** the router (categories, the 8 s throttle, clusters), the panned alarm, ping, feed, advisor at +350, Space glide, ★the button pulse, horn, the truthful ring, the arming sequence. **Fights you started stay quiet:** damage from a neutral-hostile source within 10 s and 20 m of an own attack order is a single-ring ping only, so creeping never rings the base alarm. **On-screen:** the quiet path, a single ping and nothing else. You can already see it.

---

### SM-10. Nightfall

*Dusk with the camera over the base.* **Anchor:** T0 = 18:00:00, when the tide core crosses the camera focus. Times are game time at 1× (they scale with game speed); the window is −1.8 s … +1.5 s, plus the macro beats around it.
**Built from:** WLD-02, WLD-03★, WLD-04, WLD-05, WLD-06, WLD-07, WLD-25, WLD-01, HUD-07 (+ ★clock clunk), MUS-01 (+ ★night filter), WLD-32 (base bed), CRP-01; (P1) WLD-05 strike and sputter, BLD-19 (P2) window cascade, POR-02 portrait lantern, WLD-06 hero lanterns, WLD-08 fireflies.

| t (ms) | f60 | visual (world) | audio | UI | camera |
|---|---|---|---|---|---|
| −30,000 | — | 16:30: **golden hour**, the telegraph. Warm low key light and long shadows (the sun never drops below 22° elevation and never casts toward the camera). | | (P1) The clock's golden rim glows (ambient clock). | |
| −13,000 … −300 | — | ★The tide front locks at the map's east edge (when depends on the focus) and waits off-screen without visible motion. | | | |
| −4,000 | −240 | | ★The current track starts an 8 s low-pass sweep **into night** instead of being cut. The ambience beds crossfade day→night (8 s, equal power; P0 has the base bed, the hill-country beds are P1). | | |
| **−1,800** | **−108** | | `st_dusk` starts: a lone curlew call (Ambience 2D, −10 dBFS peak, +6 dB over the beds). No wolf howl, no owl, no horns, gongs or bells. | | |
| −1,400 | −84 | ★**The nightfall tide** enters the left edge of the view at a fixed 15 m/s: a 4 m soft lead, a 6 m ink core (multiply #4C5698 at 22 %, on terrain, water, trees and props, **never on units, rings or bars**) and a 30 m trailing night side (−10 % value). Lamps and torches strike as the core passes them (lantern pools gate on over 6 m = 0.4 s). | | | |
| −90 | −5 | | | ★The clock's inner ring starts its 30° escapement step (140 ms `out_quart`). | |
| **0** | **0** | **DOWNBEAT.** The core crosses the camera focus. The sim flips `is_day()`, starts the 3.2 s sight ease and reaches the camps' sleep times. | The stinger's **low bronze hum onset** (1.8 s into the file); the clock tick; the music filter at mid-sweep; the beds at equal power. All four land on this one frame by construction (stinger scheduled from `sim_time`). | ★Clunk: a 1.5° BRONZE_RING tremor, fading over 500 ms; a clockwork clunk + tick (UI −18 dB). | **still** |
| 0 … +6,000 | 0 … 360 | **Camps settle one by one** on their own sleep signals (the sim's 0–6 s stagger, no juice hash): each leader's **closed-eye glyph** (never letters; ivory #EDE6D2, 0.36 m, ≥ 10 px) fades in over 300 ms, and on the camp's next exhale **1, 2 or 3 snore rings** rise by camp tier, outlined green, amber or red, so the count carries the tier for colour-blind players. The Crow Field's Tattiebogles (night-active) rise instead, and their crows lift off. | | | |
| 0 … +3,200 | 0 … 192 | The dark closes in on the fog edge over 3.2 s, matching the sim's sight ease (visuals never ease slower than the sim). | | | |
| +1,400 | +84 | The core leaves the right edge of the view. | | | |
| +1,500 | +90 | **Night that reads:** a view-facing fill keeps units ≥ 60 % of their noon luma and team chroma ≥ 70 %, while the world sits at 35–45 %; lamps lit; nothing is black outside unexplored ground. | | | |
| +3,200 | +192 | The sight ease is complete. | The stinger ends (5 s). | | |
| +5,000 | +300 | 18:15: the moon takes the shadows (both lights' shadow opacity is 0 at the swap). The night-side term fades out by 18:30. | | | |
| +10,000 / +20,000 | — | (P1) Heroes strike their lanterns; (P1) fireflies and moths come out, and the inn murmur begins. | | | |

**P0 floor:** golden hour, the ★tide, the stinger downbeat, ★clunk, ★music to night, lamps, night readability, sleeping camps with glyphs and snore rings, the 3.2 s fog ease. **Dawn** mirrors it: a violet pre-dawn lift at −30 s; a warm first-light core (#FFD2A0 screen at 18 %); a blackbird and one low bronze bowl tone as the downbeat; flames die as the core passes; camps rise.

---

### SM-11. Hero death

*The Uncut (Tormai, "Ilaya", `no_rotation`) falls to kingdom troops. Seen from her owner's side.* **Anchor:** `hero_died(hero, killer)`, which replaces CMB-30/31 for heroes. Heroes leave no corpse; the `Unit` persists for the revive.
**Built from:** HER-06 (+ ★soul token and the altar's mourning state), HER-01 (cracks), HVF-4 (DISSOLVE), FND-6 (braid), NTF-02; (P1) HER-06 shards flying to the killers, CMB-35 the killer's kill style.

| t (ms) | f60 | visual (world) | audio | UI | camera |
|---|---|---|---|---|---|
| **0** | **0** | The death-beat freeze (60 ms). **The sigil shatters** into its 6 segments along the HP cracks it showed below 35 % and 15 %, sliding out 0.25 m (120 ms `out_cubic`). (P1) If heroes earn XP from this death, the shards fly to them as their XP; otherwise they fade over 400 ms. | Her death vocal (Voice). | **Minimap ping:** 3 rings, white then team colour, over 1500 ms. | **never shakes** |
| 60 | 4 | **The bronze braid weight thuds to the ground first.** The braid chain goes slack (ω 3 / 2.5 / 2, ζ 0.9) and drops straight; nothing about her turns. | The weight's thud (−10 dB). | | |
| 120–520 | 7–31 | **Her silhouette:** she drops to one knee (sy 0.78, `in_out_sine`) and plants the sabre point-down in front of her, both hands on the pommel, **and stays upright**. | | | |
| **300** | **18** | | The faction **"hero down" sting** (Alerts −2 dB, 2D for owner and allies, priority 100); the killers' side hears the short "enemy hero down" (2D −6 dB) at the same time. | **Banner:** "Ilaya's braid is cut." (faction voice; never a reworded WC3 line). The portrait desaturates over 300 ms while a crack overlay draws in over 200 ms. | |
| **600–1500** | **36–90** | **Painted out**, stroke by stroke: the DISSOLVE variant's dry-brush mask, feet up (`in_out_sine`), with a MOON_SILVER #CFE0FF edge at emission 1.2 (a painted edge, never a neon rim). Ochre felt flecks shed from the edge (2 per 50 ms, reserved range) and drift on the world wind. The sabre and props dissolve with her; the dissolve takes her kneeling. | | The altar's card shows the revive cost and time. | |
| **1500** | **90** | ★**Soul token:** a bronze fleck (0.12 m, with a 6-point glint at HDR 2.4) rises from her chest to h + 1.5 m (400 ms `out_quad`) and hangs 200 ms; then it streaks home to the Naming Stones at 30 m/s with a 1.2 m tail. **Only when it arrives** (≤ 3 s, even off screen) does it strike her name stone with a ting, and **only then does her name mark go dark.** | The soul-token whistle (Spells −16 dB, 3D); the stone's ting (World −18 dB, owner and allies only). | | |

**The killers' view:** the shards fly to their heroes as XP. The soul token only fades upward, so their altar is never revealed, and they see no mourning. **The other heroes' silhouettes:** the Marshal sits back against her planted shield, which tips forward and rolls away after she is gone; the Firewright topples stiff as a plank, coughs soot, and his chimney-hat pops off; Skymirror lies back and his mirror throws one last glint at the sky. **P0 floor:** shatter, silhouette, painted-out dissolve, stings, ping, banner, portrait, ★soul token and the altar's mourning state.

---

### SM-12. Victory

*Kingdom forces bring down the last Tormai structure, the Shell Hall.* **Anchor:** `match_ended(winner_team, reason)`, the same tick as the hall's `unit_died`. World stepping halts through World's pause flag, so `interpolation_fraction()` freezes and nothing can change the result.
**Built from:** SEQ-02 (+ ★held breath, ★glide), BLD-16 / BLD-16C (hall class), AUD-01; (P1) SEQ-02 dolly, grade and cinematic shake; (P2) the Last Tableau painting.
**Time note:** the cave-in runs on `fx_time`. `Clock.fx_now` scales with `visual_rate` after the match, so from 400 ms of real time the hall falls at quarter speed. The table gives real time; the cave-in's own fx-time beats are in brackets.

| t real (ms) | f60 | visual (world) | audio | UI | camera |
|---|---|---|---|---|---|
| **0** | **0** | **The hall begins to cave in** (hall class): a flash at S 1.0 (energy-conserving, never blooms), an inhale (Y ×1.01) and a chirp shudder 12→7 Hz. ★**Held breath:** `visual_rate` eases 1.0→0.25 over 400 ms (`in_out_sine`), and with World stepping halted `Engine.time_scale = visual_rate`, the one sanctioned exception. Swings hang mid-motion; dust, smoke and embers drift at quarter speed. | Input is locked except **skip** (Esc, Space, Enter or a click). The hall's own breath: World and Combat duck −6 dB until its crack (the duck releases on the crack's fx-time crossing, not a wall-clock timer: Appendix A, R14). SFX buses start a −10 dB duck over 1200 ms; the music track fades out (1200 ms `in_quad`). | **All UI leaves within 300 ms:** the console slides out (+80 px), the top bar (−48 px) (`in_cubic`); the feed, compass, health bars, rings and pings fade to 0; the cursor overlay hides. | ★**Glide** (600 ms `in_out_cubic`) to the decisive point: the dying hall. (P1) A cinematic shake of 0.30 (7 Hz, decay 0.8/s). |
| 300 | 18 | | | The playfield is clean: no HUD at all. | |
| 400 | 24 | Quarter speed reached (cave-in age ≈ 250 ms of fx time). | | | |
| **600** | **36** | The ancient shell begins to crack along its hex seams [fx 300]. | **The victory stinger** (kingdom: a snare roll, low horns and hurdy-gurdy, resolving to the tonic; 12 s, Music 0 dB, unducked). | | The glide arrives. (P1) A 7 s dolly: distance −15 %, yaw +14°, pitch → −44°. |
| **800** | **48** | **The crack** [fx 350]: the donut plume starts in 4 staggered groups (44 puffs on a ring outside the walls, so nothing in the ruins is hidden); 6 hex plates begin to slide off as real chunks. | Crack + low boom (World −4 dB, under the SFX duck); the hall's breath releases. | | |
| 900 / 1160 / 1420 | 54 / 70 / 85 | The plates slide; the shell sinks toward its 0.5 m drop in slow motion. | Three own on-screen units shout warcries, 260 ms apart (Acks −3 dB). | | |
| 1300 | 78 | | | (P2) The tableau capture: one frame of the world only, with no HUD, banner or grade. | |
| **1400** | **84** | | | **The banner:** a burgundy #7B1E2E brush-stroke band, 120 px tall, sweeps left→right across the vertical centre (450 ms `out_cubic`); **"Victory"** stamps in (Alegreya SC 72 px, ivory #F3E6C4, 4 px ink outline, 1.4→1.0 in 160 ms `in_quad`); 10 ink spatters fly outward (120–260 px/s, 500 ms). (P1) Grade: saturation +8 % and a warm lift #FFE7B8 at 10 % over 1500 ms. | |
| 1500 | 90 | The world is a moving diorama behind the banner. | | | |
| 3,800 | 228 | [fx 1100] The gong falls last and wobbles three times like a spinning coin (COIN_SETTLE, 3→9 Hz precession, slowed 4×) under BRONZE_RING. | The gong's last note, cracked (−0.7 semitone; 3D for the winner, 2D −6 dB for the loser). | | |
| 6,500 / 8,000 | 390 / 480 | (P2) The Last Tableau: the live view cross-dissolves into a painted version of the 1300 ms capture, then 3D rendering stops. | | The Chronicle slides up; `Engine.time_scale` returns to 1.0. | |

**P0 floor:** UI exit, stinger, warcries, banner, skip, ★held breath, ★glide; the cave-in itself is BLD-16 (P0) at whatever speed is allowed. **Defeat:** a slate #3D4046 band with a torn edge; the stinger stays unresolved; a cinematic shake of 0.45; a cool, desaturating grade; at 2000 ms a single distant bell toll (kingdom) or a low gong (clans) and a gust of wind. **Juice level 0:** the banner, the stinger and the Chronicle at once, with no `visual_rate`.

---

## 3. The P0 list (slice must-haves), by engine system

**How to read it.**
- Each feature id appears once, in the system that owns its **primary file**. Its secondary hooks are named in the row.
- A row marked "P0 x / P1 y" in its domain doc lists only its P0 scope here.
- The **assets** column names what art or sound the row needs and its "runs without art" fallback (architecture rule 4).
- Paths are relative to `res://`; "new" means the file does not exist yet.
- **175 P0 rows in 16 systems**: 169 from the domain docs, plus 6 rows this bible promotes from P1 (§3.0). The per-system counts are in §3.17.

### 3.0 Bible promotions to P0

A signature moment that must land at the slice needs its parts in P0. Every promotion below is cheap ("negligible" or "trivial" in its doc), reuses a P0 system, and is the twist that makes its moment ours.

| id | promoted scope | moment | why it cannot wait | cost (domain doc) |
|---|---|---|---|---|
| ECO-04 (part) | pre-wind heave and tip; first-coin settle tinkle | SM-02 | the anticipation *is* the Hodman's character; the tinkle closes the coin's story | in the deposit's ~25 µs |
| ECO-10 (row) | chop tok steps down the pentatonic; creak; 6° lean | SM-03 | "the tree tells you it is about to fall" | negligible |
| ECO-20 (row) | "Timber!" beat | SM-03 | the look-up is the payoff of the hang | negligible |
| ECO-25 (row) | ledger phrase engine | SM-02 | "the economy plays in the key of the music": MusicClock is already P0 for ECO-04 and BLD-08 | negligible |
| ECO-27 (row) | worker flinch; Levy Horn / Sound the Gong button pulse; portrait tick | SM-09 | "the alarm points to the answer" | negligible |
| CMB-36 (row) | first-contact clash and `Vfx.battle_started` | SM-05 | announces the battle; feeds WLD-24 and the battle bed later | trivial |
| HER-03 (part) | spoke-chips and bronze flecks flying to the earning heroes | SM-06, SM-07 | cause before effect for the level-up flare; XP is never printed, so the chips are XP's only voice in the world | ≤ 0.05 ms while active |
| HER-06 (part) | soul token, plus the altar's mourning state from HER-07 (hub flame gutters, name mark dark) | SM-11 | "only then does the altar mourn" | rare, ≈ 7 sprites |
| ULT-02 (part) | the wheels' rise wave | SM-08 | the roll call needs wheels that arrive physically, never a pop-in | inside the ultimate rig |
| CAM-05 (part) | the trauma shaker itself (its policy text was already P0) | SM-08, SM-12; CMB-27 | a P0 row (CMB-27) already calls `add_trauma` | trivial |
| WLD-03 (row) | nightfall tide and first light | SM-10 | the moment's centrepiece; two shader globals | free (≈ 8 ALU) |
| HUD-07 (part) | the clock's dusk/dawn clunk | SM-10 | one of the four downbeat elements | trivial |
| MUS-01 (part) | the night low-pass filter on the playing track | SM-10 | "the music goes to night" instead of a hard switch | arbiter only |
| SEQ-02 (part) | held breath (`visual_rate`) and the 600 ms glide to the decisive point | SM-12 | without it the end is a banner over a frozen screen | trivial |

### 3.1 Fx runtime, time and the event bus (5)

| id | P0 scope | file / hook | assets (fallback) |
|---|---|---|---|
| FND-1 | `Juice` core (closed-form springs, `spring_track`, `damp`, `hash01`, `vnoise`, `crossed`, `accumulate`, Penner set); one driver loop over on-screen views (notifier cache); distance LOD; overload shedding at > 1.5 ms for 30 frames; monitors | new `src/fx/juice.gd` (static); `src/fx/vfx.gd` driver array; `UnitView.set_process(false)` + `_compose(dt)` | — |
| FND-3 | the single density governor (Calm < 14, Busy ≥ 14 (exit < 10), Brawl ≥ 36 (exit < 28)); `Vfx.allow(kind, pos, side, importance)`; balanced per-side thinning; 64 sprites per frame; impact lights through the LightBudget | `src/fx/vfx.gd`; new `src/fx/impact_lights.gd` | — |
| FND-4 | new `Events` signals (`hit_landed`, `attack_released`, `attack_missed`, `projectile_ended`, `toggle_changed`, `bounty_awarded`); the 512-record queue (handlers only enqueue; `_process` drains); def `fx` block; clip-marker baker | `src/autoload/events.gd`; `src/entities/unit.gd` (`take_damage(amount, src, flags, type_mult, origin)`, `_release()`, `prev_facing`, readers); `src/systems/combat.gd`; `src/autoload/defs.gd`; new `tools/bake_clip_markers.gd` → `data/anim_markers.json`; `docs/architecture.md` §5 in the same commit | the existing slice GLB clips |
| HVF-7 | UnitPosTex (32 × 48 RGBAF texture + CPU cache, slot allocator, `vis`); publishes `sim_time` with the lead fraction (`FxRead.lead()`, frozen on pause, never steps back) | new `src/fx/unit_pos_tex.gd` (node `World/UnitPosTex`, `process_priority` −20); new `src/fx/fx_read.gd`; `project.godot [shader_globals]` | — |
| HVF-6 | warm-up of every payoff material in the real scene (3 frames behind the loading plate, a temporary Omni + Spot light, casting shadows); preload of payoff audio | new `src/fx/fx_warmup.gd`, called from `src/main.gd`'s loading flow after FxSprites' own warm-up | — |

*Infrastructure that has no row but must exist first (§4):* `src/autoload/clock.gd`, `src/fx/juice_curves.gd`, `src/fx/juice_palette.gd`, `src/fx/render_order.gd`, `src/fx/feel_constants.gd`.

### 3.2 Unit body: composer, animation and locomotion (13)

| id | P0 scope | file / hook | assets (fallback) |
|---|---|---|---|
| FND-5 | one `AnimationTree` (MANUAL) per clip unit: loco Blend3 + TimeScale, attack and death TimeSeek, fidget OneShot; advance only on screen; 15 Hz LOD beyond 45 m (look-at is P1) | `src/entities/unit_view.gd` `_build_tree()` replaces `_play()` | slice GLB clips (attack 1.5 s, death 2.97 s, idle 4.0 s, walk/run) |
| FND-6 | weapon props on `BoneAttachment3D` following the hand (`spring_track` ω 22, ζ 0.35: 32–45 ms lag, 8–15° follow-through); weapon pose *w* (flail, braid and cloth acceleration are P1) | new `src/fx/secondary.gd`; composer layer `secondary` | B21 prop meshes as separate nodes: falchion/sword, pavise, hand-cannon, flail, javelin, sabre, staff, mirror disc, rake (fallback: merged placeholder, pose by pitch) |
| FND-7 | distance-driven stride phase, clip rate from the baked `ground_speed`, wheel angle = s / r, contact blob (r 0.6 m; heroes 0.9 m) | composer layer `loco`; new `tests/unit/test_locomotion_sync.gd` | `ground_speed` from the baker |
| CMB-01 | start push-off (+9° in 90 ms), stop plant (−8° in 70 ms, spring ω 14, ζ 0.4), faction stop flavour | layer `loco` | — |
| CMB-02 | bank into turns by gait (biped k 0.07, ≤ 10°; stiff gait pivots); reversal squash (head-lead is P1) | layer `bank` | — |
| CMB-03 | gait hysteresis (walk above 0.35 for 80 ms, idle below 0.12 for 120 ms, shuffle between), position low-pass ≤ 0.20 m, 8° yaw dead-zone | layer `smooth` | — |
| CMB-05 | desynced breathing only (2.8 s × 0.85–1.15 by hash, sy 2.5 %, ×1.15 at night) | layer `idle` | — |
| CMB-07 | toggle tells only: Plant Pavise stab, Braced Shot rest, Settle, Stand Still | layer `stance`; `Events.toggle_changed` | ramrod and forked rest props (fallback: weapon pose only) |
| CMB-13 | ack styles (hop / salute / bow / stomp / crew; `what` chin-up), ≤ 1 per 700 ms; speaker shimmer | layer `ack`; `Audio.voice_started`; shimmer in `src/fx/selection_circles.gd` | — |
| CMB-16 | swing remap: load, snap, hold (visual hit-stop), recover per weapon; the contact pose lands on the damage tick; whoosh peak on contact; a cancelled swing relaxes | replaces `UnitView._animate_swing()`; `Juice.anticipate()` (§4.2); new `tests/unit/test_swing_pose.gd` | `data/sfx_meta.json` `peak_ms` per whoosh sample |
| CMB-21 | mass-scaled knockback (ω = clamp(24/√m, 12, 30), ζ = clamp(0.5 + 0.08(m − 1), 0.46, 0.8)), heavy absorb branch, tilt, 90 ms tremble; rings and bars never move | layer `react` | — |
| CMB-30 | 60 ms death beat; death styles away from the origin; contact dust and body-fall; overkill launch; props detach (the hat pop is P1) | replaces `UnitView._animate_death()`; a wreck pool of 8 | `fall_light`, `fall_armoured`, `fall_huge` (3 variants each) |
| ECO-03 | hod, bag and logs as skinned sub-meshes chosen by `prop_sel`; the `Cargo` bone spring (`CargoSway`); laden walk; hoist (the tool swap is P1) | new `src/fx/cargo_sway.gd` (`SkeletonModifier3D`); `prop_sel` / `prop_aux` uniforms; composer layer `cargo` | worker GLBs with prop sub-meshes (≤ 150 vertices each) + a `Cargo` bone from the auto-rig; a `walk_laden` procedural clip (fallback: ProcMesh parts and `prop_anim`) |

### 3.3 Unit shader and material variants (3)

| id | P0 scope | file / hook | assets (fallback) |
|---|---|---|---|
| CMB-17 | energy-conserving rim flash (0–30 ms peak #FFF6EC, latched; 30–80 ms → #FF5A48); `ALBEDO × (1 − 0.6f)`, `EMISSION += tint × 0.45f`; peak ≤ 0.95 linear | new `src/entities/unit.gdshader` with the fixed uniform map (Appendix A, R4); the placeholder shader gets the same maths; new `tests/render/test_flash_luminance.gd` | a team mask per GLB (import step) |
| CMB-31 | team-colour ebb (`team_sat` 1→0.2, feet→head, from 0.7 s over 1.4 s) + the sink at 6.5–8.0 s (dissolve and remains are P1) | `unit.gdshader` `team_sat`, `sat_front`; `src/fx/proc_mesh.gd` writes the team mask to `COLOR.a` | — |
| HVF-4 | `status_a`, `status_t`, `rim_col`; DISSOLVE (brush stroke) and DITHER (hatching) variants per surface through `Variants`; the `material_overlay` hook (sketch outline, shimmer, Brawl hero outline) | `unit.gdshader`; new `src/fx/unit_variants.gd`; `UnitView.set_variant()`, `set_status()`; new `unit_status_overlay.gdshader` | `assets/fx/brush_mask.png` 256² R8, `assets/fx/hatch.png` 64² R8 (procedural streaks and lines) |

### 3.4 Particle and ground primitives (4)

| id | P0 scope | file / hook | assets (fallback) |
|---|---|---|---|
| FND-2 | FxSprites: cutout, soft and additive MultiMesh layers + 3 chunk layers; analytic motion (BALLISTIC / BOUNCE / FLUTTER / ORBIT, GROUND, facing); packing; slot life classes with the 50 % rejection rule; the economy sign-bit extensions (STREAM, SETTLE, ERODE); the heroes' importance-3 reserve | new `src/fx/fx_sprites.gd`, `fx_sprite.gdshader`, `fx_chunk.gdshader`; facades `Vfx.spawn`, `burst`, `stream_start`, `stream_stop`; new `tests/render/test_fx_packing.gd` | painted 4 × 4 atlas sheets, one atlas per layer (Appendix A, R5; Appendix B); a halo sprite for Compatibility |
| HVF-2 | cliff-exact `terrain_corners`; GroundZones patches (large, small, glyph) and strips (edge, timer) with all modes; swap-remove compaction | `src/world/terrain_builder.gd` upload; new `src/fx/ground_zones.gd`, `ground_zone.gdshader`, `ground_strip.gdshader`, `src/fx/terrain_h.gdshaderinc` | the glyph `Texture2DArray` (fallback: SDF shapes) |
| HVF-5 | school kit and the named-sprite vocabulary (no anonymous dots) | new `src/fx/school.gd`; `data/fx_schools.json`, `data/fx_recipes.json` | 8 cast glyphs (512² array) + 8 crack masks + 3 stroke layers; 2 head/feet glyph sheets; 24 named frames (fallback: in-shader SDF) |
| HVF-8 | AttachFx: unit-local loops from UnitPosTex (`BURN`, `STEAM`, `WIND_STREAKS`, `FILM_GRAINS`, `MIST`, `DRIP`, `ZONE_TONGUE`) | new `src/fx/attach_fx.gd` + `attach_fx.gdshader` | flame tongue, ember, steam curl and dust frames |

### 3.5 Combat impacts and missiles (9)

| id | P0 scope | file / hook | assets (fallback) |
|---|---|---|---|
| CMB-18 | material × weapon sparks for flesh, metal, wood, stone, straw and soot; frontal-arc material; the Gore setting | `src/fx/vfx.gd` router → FxSprites | atlas: star, streak, splinter, chip, droplet, straw, puff; SFX `hit_metal/wood/flesh_l` and `_h` (4 each), `hit_stone` 4, `hit_straw` 4 |
| CMB-20 | painted swing smears (shape per weapon, reveal 0.15·dp, fade 80 + 20·mass ≤ 140 ms, always outside the hull) | new `src/fx/smears.gd` + `smear.gdshader` (pool 24, Compatibility 8) | a dry-brush stroke 256 × 64 greyscale (fallback: a gradient arc) |
| CMB-22 | crit punch: 80 ms hold, smear ×1.3 at HDR 1.8, 110 ms victim flash, knockback ×1.6, ground shock ring 0.4→1.4 m, "N!" | `vfx.gd` + layer `react` | `hit_crit` ×3; shock-ring sprite |
| CMB-23 | whiff (smear and whoosh only); miss dodge 0.12 m + "miss" text (local only); ranged misses carry on and stick | `vfx.gd` + layer `react` | — |
| CMB-24 | ranged release tells: gun (ember, fizz, muzzle star HDR 3.0, smoke ring, recoil); thrower (crow-hop); casters (gust, glint, coal, crow, smoker) | `unit_view.gd` poses; `vfx.gd`; `src/entities/projectile.gd` visual children | `hookgun_fire`, `javelin_throw`, `gust_bolt`, caster bolts; smoke, ember, feather and leaf frames |
| CMB-25 | javelin ground stick (wobble ω 37.7, ζ 0.18; lives 6 s; ring of 64) (pincushion and pass-through are P1) | new `src/fx/stuck_javelins.gd` (1 MultiMesh) | javelin mesh (prop kit); `javelin_hit` earth thunk |
| CMB-26 | missile flight: javelin wobble 4° at 6 Hz; coal and pots tumble | `projectile.gd` visual child; `Projectile.progress()` | coal and clay-pot meshes (procedural) |
| CMB-27 | siege, powder and mechanical: linstock, covered ears, roll-back and shove, smoke, whistle, impact, scorch, ground shadow, `Atmos.shock`, trauma 0.35 / 0.25 | `vfx.gd`, `projectile.gd`, `impact_lights.gd`, `CameraJuice.add_trauma()` | `bombard_fire`, `slingcart_throw`, `shot_whistle` ×3, `bombard_hit`, `claypot_hit`, ratchet tick; clod, shard and smoke frames |
| CMB-36★ | first-contact clash: one boosted impact + a dust ring + the clash layer; emits `Vfx.battle_started(pos)` | `vfx.gd` (a 12 m cell grid of last-hit times) | reuses `hit_metal_h` + `hit_wood_l` |

### 3.6 Orders, selection, cursor and picking (9)

| id | P0 scope | file / hook | assets (fallback) |
|---|---|---|---|
| UCA-F4 | ScreenQuery: `is_pickable` (the only UI visibility predicate), `pick`, `box`, `on_screen`, `in_view` | new `src/input/screen_query.gd`; `Selection.pick_unit()` and `_box_select()` become wrappers; cached `Unit.pick_h` | — |
| CMB-08 | shape-coded markers (move rings + pin, attack chevrons, patrol arrows, attack-ground crosshair), spam taps, pool of 8 | new `src/fx/order_markers.gd` (1 MultiMesh, 16 instances, curves on `ui_time`) replaces `CommandInput._marker()` | SDF shapes; the dust frame |
| CMB-09 | target flash: 3 blinks; enemy ring with 4 notches; rim pulse; trees shudder | `selection_circles.gd` transient list | — |
| CMB-10 | order ripple, 28 ms per rank, ≤ 308 ms; ring pulse ×1.22; faction nod | `selection_circles.gd` pulse map; layer `ack` | — |
| SEL-01 | ring pop-in that paints in (0.80→1.06→1.00, thickness 1.4→1.0), box delay ≤ 140 ms; a quiet deselect ghost | `selection_circles.gd` + `ring.gdshader` (`ui_now`) | — |
| SEL-02 | hover rim, ring and bar (the nameplate is P1) | `src/input/selection.gd` → `ScreenQuery.pick()`; `UnitView.set_rim_boost()` | — |
| SEL-03 | crafted drag box + the "12 / 17" count badge (the live preview is P1) | `selection.gd` `_draw()` via `ScreenQuery.box()` | faction box frame (fallback: drawn lines) |
| CUR-01 | hardware cursor slots per faction and size, fixed hotspots (pressed and tassel are P1) | new `src/ui/cursors.gd` | `assets/ui/cursors/<faction>/`, painted at 256 px and cleaned at 32/48/64 px |
| CUR-02 | context states: notched tip over enemies, targeting reticle, invalid, gather badges, edge-pan arrow (lock-on is P1) | `cursors.gd` reads `Selection.hovered`, `CommandInput.targeting_changed`, `RtsCamera.edge_dir` | the same cursor set |

### 3.7 Floating text and health bars (2)

| id | P0 scope | file / hook | assets (fallback) |
|---|---|---|---|
| CMB-28 | text policy *Minimal* (crits, bounty, heals ≥ 10, mana drained or absorbed, misses involving the local player); crit "N!" pop; bounty "+N" with a coin; merge within 250 ms (the coin flight and *Detailed* mode are P1) | `vfx.gd` `show_text()` → PopupText (§4.5; Appendix A, R2); new policy module `src/fx/combat_text.gd` | the PopupText atlas (digits, signs, coin, log) |
| CMB-29 | bar ramp, damage ghost (holds 400 ms, then `damp` 7/s), latched 70 ms border flash; flag bits (heroes 0–4, economy 5–6) (the hatch, reveal and hero border are P1) | `src/fx/health_bars.gd` + `health_bar.gdshader` (`ui_time` / `fx_time`, never `TIME`) | — |

*PopupText itself (economy §2.3) is infrastructure (§4.5) and is built in wave 1.*

### 3.8 Economy and workers (12)

| id | P0 scope | file / hook | assets (fallback) |
|---|---|---|---|
| ECO-01 | mine gulp and spit: lintel sag, a habituating door glow, ore dust, the hod comes out heaped and the bag is dragged out (the interior loop and exit anticipation are P1) | new `src/fx/economy_fx.gd`; MineFx (`src/fx/mine_fx.gd`); mine part tags (lintel, door) | mine GLB part tags; mine creak, door thump, effort huff, felt drag scuff |
| ECO-04 (+★) | deposit: the hod tipped into the counting hatch, or the clans bow at the felt flap; the heap flight landing on a 16th; hatch flap; coin spill with SETTLE; popup; jingle; ★pre-wind and settle tinkle | `economy_fx.gd`; `CargoSway`; FxSprites HEAP / BILLET / COIN; PopupText; `Audio.schedule_3d()`; `MusicClock.beat_at()` | a counting hatch (part 13/1) on kingdom drop-offs; a felt door flap on clans halls; atlas cells 32–35; hatch clack, coin jingle, settle tinkle, felt thup, bag clink, billet clatter |
| ECO-06 | mine-low warning: an amber minimap ping, one advisor line per mine, a feed line, the lanterns blink twice (the vein is P1) | `economy_fx.gd`; `Minimap.ping()` | an advisor line per faction |
| ECO-08 | the chop swing (not a hammer tap): hang at the top, a 70/90 ms visual hold, 3–5 chips, the tok | composer layer `work`; `economy_fx.gd` | `eco_chop_tok` ×3, leaf rustle; chip frames |
| ECO-09 | tree shudder (θ = 0.06 rad · e^(−6t) · sin(2π·5.5t), canopy lagging 40 ms) via the split timestamp (leaves are P1) | `src/world/doodads.gd` (`use_custom_data` before `instance_count`); new `tree_common.gdshaderinc`; `tree.gdshader` | — |
| ECO-10★ | the chop tok steps down the pentatonic as the tree empties; a creak at ≤ 10 %; 6° lean | as ECO-09; `MusicClock.note()` | 3 tok samples recorded at C5 |
| ECO-11 | topple: 8-direction scoring (−3 toward the camera), hesitation, ^2.2 fall, bounce, leaves, dust, a permanent stump, a sawdust ring; FallingTreePool with the 2 nearest keeping shadows (logs and litter are P1) | `doodads.gd`; new `tree_falling.gdshader`; new `src/fx/stumps.gd` (1 MultiMesh) | creak, whoosh, crash; stump (procedural cylinder) |
| ECO-20★ | "Timber!": the chopper steps back and looks up; neighbours flinch; "Hup!" / "Hai!" | composer layers `work` + `fidget` | 2 barks per faction |
| ECO-21 | Levy Horn: horn, the truthful 22 m terrain ring, nods, the 1.5 s arming sequence, the return to work (the flag timer and the sliver are P1) | composer layer `levy`; `prop_sel`; FND-6 flail; new `src/fx/eco_rings.gd` + `eco_rings.gdshaderinc` in `src/world/terrain.gdshader` | two-note wooden horn, chain rattle, clank, "Ready" and "Back to it" lines; kettle hat and flail props |
| ECO-22 | Sound the Gong / Roll the Felt: a pendulum gong with BRONZE_RING, the 30 m ring, cargo cinch, skirt roll, felt knots, kept cargo on lattice hooks (the slings are P1) | `economy_fx.gd`; part tag 12; MineFx `KNOTS`; SiteParts torus; GroundProps hooks | door-gong boom + all-clear tap; a skirt part on yurts |
| ECO-25★ | ledger phrase engine: composed motifs on the MusicClock grid; brightness = saturation; habituation | `economy_fx.gd`; `MusicClock`; `Audio.schedule_3d()` | coin-bell + woodblock (kingdom), bowl tap + log drum (clans), recorded at C5 |
| ECO-27★ | harass alarm: own workers flinch and glance; the hall's Levy Horn / Sound the Gong button pulses (urgent clock); the hall portrait ticks | `economy_fx.gd`; `src/ui/command_card.gd`; `hud_pulse.gd`; body-yaw glance (FND-5 look-at is P1) | portrait tick (UI) |

### 3.9 Buildings (21)

| id | P0 scope | file / hook | assets (fallback) |
|---|---|---|---|
| BLD-01 | surveyor's sketch ghost (paper fill, inverted-hull ink, light-direction hatching, an 8 Hz line boil); SPRING_GLIDE (ω 40, ζ 0.72); the valid tock | new `src/input/build_placement.gd`; new `sketch.gdshader` (3 passes) | 128² paper grain (shared with world); tock |
| BLD-02 | footprint grid (valid, or hatched invalid); fog-honest blocker callouts; a reason line | GroundZones `GRID`; a `placement_state` L8 texture | — |
| BLD-04 | stamp + ink blot (the stakes and failed arrival are P1) | `build_placement.gd`; GroundZones `INK_BLOT` | mallet-on-paper stamp |
| BLD-05 | foundation: packed earth, sill settle or stone ring, a unit-aware dust skirt, the thoomp | new `src/fx/building_fx.gd`; GroundZones `PACKED_EARTH` | foundation thoomp + gravel |
| BLD-06 | course-laid reveal latched to strikes; the fresh strip; the edge band; inside faces; a silhouette-preview overlay on the nearest 1–3 sites | the `structure_build.gdshader` swap; new `src/fx/structure_uniforms.gd` (`build_a`, `build_b`); `sketch.gdshader` as overlay | ProcMesh wall subdivision; baked masks |
| BLD-07K | scaffold-raised: poles, ledgers, braces, ladder, lifts, rafters at 50 %, the bare pole at 75 %, the crown staged and hoisted at 82–93 %, scaffold collapse + fwump | `building_fx.gd`; new `src/fx/site_parts.gd` (4 MultiMeshes); part tags 7, 8, 9 | crown props per def; wood knocks, clatter, fwump, rope creak |
| BLD-07C | Raising: stone ring, lattice, poles, the felt-roll torus, bands; the gong staged at the door; the completion gong strike | `building_fx.gd`; SiteParts incl. new `site_torus.gdshader`; part tags 4, 10 | lattice panel texture; gong swell, felt fwip |
| BLD-08 | builder strikes on the MusicClock grid (per-site subdivisions 0, ½, ¼, ¾; ±10–20 ms humanisation); Hod Chain density; the hammer pose; timbre and particles by course material; ≤ 2 beds (pitch and the work song are P1) | composer layer `work`; `building_fx.gd`; `MusicClock`; `Audio.schedule_3d()` | chisel tink, mallet tok, felt thup, lattice clack; 1 construction bed per faction |
| BLD-09 | completion: the last strip, edge flash ×2.5, SETTLE by material, banner hoist + CLOTH ×2.2, windows, cues; off-screen advisor + feed; no ping (the unlock light-catch is P1) | `building_fx.gd` sequence; `command_card.gd` | faction complete cues ×2 (+ 0.6 s short variants); job-done lines |
| BLD-11 | barracks work loops only: the Drill Yard dummy (thwacked every 2 steps) and the Grapple Yard wrestlers (orbit per 5 steps, slap every 2nd) | part tag 15 work parts + the `work` uniform; `building_fx.gd` | thwack, slap; work-part pivots in `CUSTOM0` |
| BLD-12 | door exit: a door FLARE ≤ 1.0; the walk-out `visual_offset` (≤ 1.6× walk speed); a push-through squash; rings, bars and picking follow the offset | composer layer `spawn`; `UnitView.visual_offset()`, read by HealthBars, SelectionCircles, Selection and UnitPosTex | door part tag; door creak |
| BLD-13 | rally flag thrown down, stabbing in (a 9° pole wobble, ω 18, ζ 0.25), a plaque on a mine or tree, the route `DASH_STRIP`; Alt shows every flag | new `src/fx/markers.gd` (RallyMarkers); GroundZones `DASH_STRIP` | rally plant thunk; pennant cloth (WLD-29) |
| BLD-14 | research toast (`UiJuice.enter`) and card overlay; diegetic marks on sign boards and mast ribbons (the ripple is P1) | `message_feed.gd` (the old `toast.gd` becomes a feed line); part tag 17 + `anim_c.w` | mark slots in the building art; quench hiss + anvil ring / pour + bowl ring |
| BLD-15 | hit chips + the material HIT motion; scars (a 4-slot ring; siege bites); flash heat gate ≤ 2.5 Hz; S1 smoke; S2 flame cards on every burning building + sprite fire on the 5 nearest; S3; fire splats in the lantern map; one crackle bed; fog freeze (real lights are P1) | `building_fx.gd` state machine; `dmg`, `scar0–3`, `fxfr`; part 14 flame cards appended at import; FxSprites stream regions A and E | baked crack, seam and panel masks; flame tongue and smoke cut-out cells; crackle bed; heavy thud |
| BLD-16 | cave-in: inhale, roof sag, ridge snap (crack + boom), walls hinge out, donut plume (12 / 24 / 44), clean-up inside the dust, settle, rubble (the banner fall and the hall's held breath are P1) | the structure branch of `_animate_death` → build variant with `build_mode` = destroy; `building_fx.gd`; new `src/fx/rubble_props.gd` | groan, crack, rumble, patter, creak; plaster, tile, felt and shell shard cells |
| BLD-16K | the crown rides the roof, falls, rolls 1.5 m with BRONZE_RING, COIN_SETTLE; the cracked hall bell (the stork is P2) | as BLD-16 | crown meshes; cracked bell |
| BLD-16C | felt tears (8 flaps), the lattice folds, the gong falls last and wobbles (COIN_SETTLE 3→9 Hz); Shell Hall plates slide off; the cracked gong | as BLD-16 | felt rip; gong; shell plates as `chunk_l` |
| BLD-18 | a select voice per building + a team-tinted fresnel rim pulse + RECEIVE at 0.5× (the gags are P2) | selection hook in `building_fx.gd`; `fxfr.y` | `bld_<def>_select` one-shots for every slice building and the gold mine |
| BLD-20 | hall tier-up: scaffold or masts around the hall, the door shuts, a swap-line reveal through the old mesh, the crown last, the ceremony (bell ×3 / gongs ×3, fanfare), the HUD tier stamp (pennants and the raised-tool wave are P1) | `building_fx.gd`; two `MeshInstance3D`s during the upgrade | T2 hall meshes; town bell; a tier fanfare per faction |
| BLD-24 | completion predictor; accelerando from t_done − 1.2 s; a shared wind-up at t_done − 510 ms so the final blow lands on the completion tick; the miss fallback (topping-out is P1) | `building_fx.gd` predictor | scaffold creak |
| BLD-25 | unattended site: the edge band fades, the bed stops, a mallet glyph after 3 s (left tools and the swinging rope are P1) | `building_fx.gd`; PopupText | — |

### 3.10 Heroes (7)

| id | P0 scope | file / hook | assets (fallback) |
|---|---|---|---|
| HER-01 | sigil: 10 level segments, the ownership line, band modes (XP arc, gem, cast, channel, lock, will-travel, aura pips), HP cracks, the min-px clamp, never blooms (the ratchet walk, ripples, gem glint and click answers are P1) | new `src/fx/hero_sigils.gd` + `hero_sigil.gdshader` | sigil faces (wheel, gong, neutral) and crack masks in the glyph array (fallback: SDF) |
| HER-03 (+★) | HUD XP pour and wrap; ★spoke-chips and bronze flecks flying to the earning heroes (≤ 0.75 s), direct in 180 ms when a level is crossed (the shards and the fizzle are P1) | new `src/fx/xp_motes.gd` (32-slot MultiMesh); new `src/ui/hero_bar.gd` | spoke-chip and bronze-fleck frames; ivory click and bronze ting (`pitch_locked`) |
| HER-04 | wind-up; the per-hero level pose; the standing emblem (stands to face the camera; kingdom ratchet, Tormai strike); slam; numeral; cue + ladder bell; line at 1150 ms; portrait flip and wrap (the pillar, multi-level arpeggio, light and wear are P1) | new `src/fx/hero_fx.gd`; the standing-emblem MultiMesh in `hero_sigils.gd`; `hero_bar.gd`; composer layer `level_pose` | the level-up cue for each faction (on D, 1.4 s); 36 ladder bells (9 × 2 pentatonic families × 2 factions); 4 level lines per hero; pawl clack |
| HER-05 | the "+N" skill pip; learning drops the icon into its rank frame; denial (mana, cooldown, invalid target) shakes and fizzes (ready sweeps, the taste, the body denial and the retrain are P1) | `command_card.gd`, `hero_bar.gd`, `src/ui/hud.gd` | page turn, fizz; "need mana" lines |
| HER-06 (+★) | death beat; the sigil shatters along its cracks; the per-hero silhouette; painted-out DISSOLVE with faction flecks; stings; ping; banner; portrait; ★the soul token and the altar's mourning state (shards to the killers, the shield roll and the hat smoke are P1) | `hero_fx.gd`; DISSOLVE; FND-6 braid; `hero_bar.gd`; `Minimap.ping()` | death props (wheel-shield, chimney-hat); hero-down stings ×2 + enemy hero down; death vocals; soul whistle |
| HER-07 | revive completion: a soft ring, a fresnel pillar, painted in top-down (targetable from frame 0), landing squash, segments fly in, the portrait floods back, an own ping (the progress dressing and the inn revive are P1) | `hero_fx.gd`; Beams; GroundZones | revive swell |
| HER-08 | a hero leaves the altar: kneel → rise; the kingdom sigil peels off the floor wheel and rolls to the hero's feet; the Tormai sigil skims on a gust; the Ready line (name marks, the gong frame and the motif are P1) | `hero_fx.gd`; altar part tags `FloorWheel`, `Stone1..6`, `GongFrame`; a SpellFx cosmetic rig | altar part tags; deep clank; Ready lines |

### 3.11 Spells, statuses, summons and ultimates (20)

| id | P0 scope | file / hook | assets (fallback) |
|---|---|---|---|
| HVF-1 | SpellFx recipe player (anticipation / release / linger), protected record classes, 16 rigs with 4 reserved for ultimates, rank scaling | new `src/fx/spell_fx.gd`; `Defs.fx_recipe(id)` | `data/fx_recipes.json` |
| HVF-3 | StatusFx feet, head and coil layers on UnitPosTex and `sim_time`; the HealthBars packing | new `src/fx/status_fx.gd`, `status_glyph.gdshader`, `root_coil.gdshader`; `health_bars.gd` | head/feet glyph sheets; a root-coil mesh (procedural) |
| ABL-01 | spell grammar: prop + class pose + the sigil cast mode (three clicks, three swells or three slashes); dialect bursts at c = 0.5 and 1; pre-launched travel; release hold by class; effort vocal; the riser aligned on `peak_s`; cancel → chalk dashes | `spell_fx.gd`; `FxRead.cast_progress()`; composer layer `cast` | school risers with `peak_s`; 1–2 effort vocals per hero |
| ABL-02 | truthful, terrain-draped reticles (circle, donut, cone, rect); edges coded by allegiance | new `src/input/ability_targeting.gd` (owned by `CommandInput`) | — |
| ABL-03 | the range ring (walk-to and queue glyphs are P1) | `ability_targeting.gd`; strip `EDGE_DASHED` | — |
| ABL-05 | missiles, cones and trails with back-dated accumulators | `spell_fx.gd`; `projectile.gd`; Beams | school frames |
| ABL-06 | ground zones: truthful radii, smooth / notched / dashed edges, fill stacking, fire that pulses on `zone_ticked` and leans toward its victims | `ground_zones.gd`; AttachFx `ZONE_TONGUE`; `Audio.loop_3d()` | fire loop |
| ABL-07 | diegetic timers: the Fuse Mark cord with defuse, the sigil channel arc, the keg rack | StatusFx feet `FUSE`; strip `TIMER_ARC` | fuse hiss |
| STS-01 | grammar: feet = buffs, body = afflictions, head = control; one head glyph at most | `status_fx.gd`; `unit.gdshader` `status_a` | — |
| STS-02 | aura feet glyphs + cadence pops and ring (stamps and tick rules are P1) | `status_fx.gd`; strip `PULSE` | — |
| STS-03 | stun stars that fall one per 0.5 s (in the shader from `sim_time`); root coils that unwind | StatusFx head layer (one instance per unit); the coil MultiMesh | star frame |
| STS-04 | frost, dust and soot body films (stone dust and chaff are P1) | `unit.gdshader` (HVF-4); AttachFx | — |
| STS-05 | burning, blind, silence, mark | StatusFx; AttachFx `BURN` | — |
| STS-07 | invisibility: own units as a hatched under-drawing (DITHER), detection ghosts, the fog gate | DITHER + overlay; `status_fx.gd`; `Vfx.allow()` | the hatch texture |
| SUM-01 | summons arrive, count down in their own material (life rings), and unmake into what they leave (Hail-Swift pellets exactly on the 2 m patch for 2 s) | `spell_fx.gd`; StatusFx life ring; AttachFx `DRIP` | hail pellet frames |
| ULT-01 | the ultimate frame: an owner vignette at α 0.14 outside 55 % of the radius with a painted edge; the stinger (2D owner, 3D others); the shout on release; the gameplay edge (ducks and `Atmos.shock` are P1; trauma via CAM-05★) | new `src/fx/screen_tint.gd` (CanvasLayer 1) | an ultimate stinger and a shout per hero |
| ULT-02 (+★) | Wagon Ring: the 11 m capture ring over the cast point; ★the rise wave; the roll call with lock rims; the hand-off onto the units; draining lock rims; lethal block (sky-wheel clicks and the payoff stamp are P1) | `spell_fx.gd` ultimate rig (a 13-instance MultiMesh, sorted back-to-front on the CPU); StatusFx `LOCK_RIM` | wagon wheel mesh (fallback: torus + 6 boxes); rumble, clink, clang, chain loop, bell |
| ULT-03 | Grand Bombard: crate, crew, the keg-rack timer | ultimate rig: crate + a 10-keg MultiMesh; CMB-27 hooks | crate, keg and bombard meshes (procedural) |
| ULT-04 | Through the Tall Grass: the grass ring, straight wind streaks, the line slash, the shrug (film −2) | rig: a 40-instance grass MultiMesh; AttachFx; the smear pool | — |
| ULT-05 | Swallowed Sun: disc and corona, `GLOAM_DARK`, the curtain | Beams alpha + additive; GroundZones `GLOAM_DARK` | eclipse disc and corona (procedural) |

### 3.12 Items, loot, shops and creep camps (9)

| id | P0 scope | file / hook | assets (fallback) |
|---|---|---|---|
| ITM-01 | a bouncing drop (closed form, ending exactly on the sim item), parcels, rolls and props by class, rarity rays coded by shape (the tier D crown and the night glow are P1) | new `src/fx/loot_fx.gd` (4 MultiMeshes + glows) | parcel, roll and power-up prop meshes (procedural); loot chimes ×4 tiers |
| ITM-02 | pickup (the seal snaps, the twine pops, the parcel goes under an arm), slot pop, the five power-up gestures, purse, strawberries (full pack and "?" are P1) | `loot_fx.gd`; `hud.gd` inventory | seal snap, twine pop |
| ITM-03 | consumables: salves, draughts, tinctures, teas (with the break flash), Chalk, Flour Bomb, charges | `spell_fx.gd` item recipes; StatusFx; AttachFx | tea steam, flour and chalk frames |
| ITM-04 | recall: Homeward Horn, Homeward Felt, Homing Pigeon; will-travel dashes; afterimage cards | `spell_fx.gd`; strips; a carpet rig; a 12-card MultiMesh | horn, felt roll, pigeon flap |
| ITM-05 | shops: purchase coins; the Weighstall beam weighs the coin; toss; stock tag; give; drop | `loot_fx.gd`; Weighstall structure parts `Beam`, `PanL`, `PanR`; `hud.gd` / `command_card.gd` | Weighstall part tags; coin into the pan; beam creak |
| CRP-01 | Cairnwake lichen glow at night; crows perch and lift off (hood smoke, lantern heads and the crows' return are P1) | new `src/fx/creep_fx.gd`; a crow-prop MultiMesh (24) | crow prop; lichen emission mask |
| CRP-02 | the same-frame "!" / "‼" and head snap for the whole camp; the family startle with a 0–90 ms body stagger (roars are P1) | `creep_fx.gd`; StatusFx head layer; startle clips per `fx.family` | startle barks per family |
| CRP-04 | camp cleared: the 1.6 s faction stinger, the merged summary stamp (the dressing topple, settling dust and coins are P1) | `creep_fx.gd`; PopupText; `Audio.play_ui()` | a camp stinger per faction |
| WLD-07 | sleeping camps: pose, the closed-eye glyph (never letters), snore rings counted by tier, minimap state (family idles and sounds are P1) | composer layer `sleep`; new `src/world/camp_fx.gd`; the StatusFx head layer (Appendix A, R17); FxSprites soft ring | closed-eye glyph and snore-ring cells |

### 3.13 World and atmosphere (22)

| id | P0 scope | file / hook | assets (fallback) |
|---|---|---|---|
| WLD-F1 | Atmos director: scroll integration on the sim clock, globals, signals, monitors | new `src/world/atmos.gd` (`World/Atmos`) | — |
| WLD-F2 | the shared world shader include (wind lag and recoil, cloud shadow, fog smoothing, memory grade, tide, night gate, lanterns) and its quality tier; removes `TIME` from `tree.gdshader` and `water.gdshader` | new `src/world/shaders/world_common.gdshaderinc`, `foliage.gdshaderinc`, `cloth.gdshaderinc` | `atm_noise_tex`, `atm_detail_tex` (fallback: `FastNoiseLite` seamless images) |
| WLD-F3 | wind and weather state (closed-form direction, seeded schedule, CPU mirror) | new `src/world/weather.gd` | — |
| WLD-F4 | the lantern map: light without lights (the house-light pool and the LightBudget are P1) | new `src/world/lanterns.gd`, `src/fx/light_budget.gd` | — |
| WLD-F5 | the atmosphere governor: presets, zoom, game speed, auto-degrade | `atmos.gd`; `Settings` keys | — |
| WLD-F6 | biome data and derived maps | new `src/world/world_maps.gd`; `data/biomes.json` | — |
| WLD-01 | sun and moon with one shadow owner, swapping at 18:15 / 05:40; shadows never toward the camera | `src/world/day_night.gd` becomes the director, + a Moon light | — |
| WLD-02 | time-of-day grading and the golden-hour telegraph (per-night variation is P1) | `data/time_of_day/greenvale.tres`; `day_night.gd` → `Environment` | — |
| WLD-03★ | the nightfall tide: an ink front at 15 m/s, its core on the focus at T0, lamps igniting as it passes; the mirrored dawn | `atm_front`, `atm_front_t`; `atm_tide()`, `atm_night_gate()` in the include | — |
| WLD-05 | lights of dusk: emissive lamps and their pools (strike and sputter are P1) | `prop.gdshader` `atm_ignite()`; the lantern map | lamp emissive masks |
| WLD-06 | night readability: a view-facing unit fill, team lift, a moon rim (the lantern response and hero lanterns are P1) | `unit.gdshader` includes `world_common` | — |
| WLD-09 | cloud shadows (≤ 0.32 on the ground, ≤ 0.19 on units, never on rings or bars) | `atm_cloud_shadow()` | the painted cloud mask (noise channel A) |
| WLD-10 | one wind field with lag for grass, trees and cloth (recoil, sheen and whoosh are P1) | the noise texture + `atm_wind`; `foliage.gdshaderinc`; `Atmos.gust_at()` | — |
| WLD-14 | tree sway with hierarchy and inertia | `tree.gdshader` + the foliage include | — |
| WLD-15 | the grass wrap lattice, density and fade | new `src/world/grass.gd` + `grass.gdshader` | a grass tuft atlas 1024² (procedural) |
| WLD-18 | shores by body size | `water.gdshader`, `terrain.gdshader` | — |
| WLD-19 | water colour and painted shimmer (glints and splashes are P1) | `water.gdshader` | water stroke normals |
| WLD-20 | wading rings and bow wake at the Hale Spring | `unit_view.gd` → `Vfx` → FxSprites ring kind | ring frame; `lp_wading` |
| WLD-25 | the fog edge: asymmetric smoothing (concealment within one upload, reveal eases), a painterly edge, the 3.2 s dusk sight ease | new `src/world/fog.gd` (double buffer, display bytes, `atm_fog_blend`) | — |
| WLD-27 | the remembered world graded (still and faded) + tree memory (stillness and grain are P1) | `atm_memory_grade()`; `doodads.gd` `remembered_felled` | paper grain |
| WLD-29 | cloth for banners, rally flags, back-banners and tents | `cloth.gdshaderinc` | cloth materials named `*CLOTH*` or a vertex mask |
| WLD-42 | the Hale Spring set piece (the night-ambush dell: the Crow Field awake, fireflies, wading) | landmark data + the rows above | `lp_spring` |

### 3.14 Camera (7)

| id | P0 scope | file / hook | assets (fallback) |
|---|---|---|---|
| UCA-F2 | one composer with PLAYER / GLIDE / CINEMATIC modes, exact maths, honest picking through the shaken transform, the listener follow | refactor `src/input/rts_camera.gd`; new `src/input/camera_juice.gd` | — |
| CAM-01 | pan: the exact velocity approach, a crisp start, a firm stop (≤ 150 ms), soft bounds (sprint is P1) | `rts_camera.gd` `_process` (dt from `Clock.ui_dt`) | — |
| CAM-02 | exact grab-drag (fling is P2) | `_drag_by()` with a ray from the stored base transform | — |
| CAM-03 | zoom: same-frame steps (≥ 15 % of a notch on the first frame), pitch coupling, the end-stop kick (zoom-to-cursor is P1) | `rts_camera.gd` `pitch_for(d)`, the kick spring | — |
| CAM-04 | jumps: an `out_quart` glide, T = 150 + 55·log2(1 + D/12) ≤ 330 ms; Space (the veil, breadcrumbs, arrival ripple and return crumb are P1) | `glide_to()`; `AlertRouter.next_jump()` | — |
| CAM-05 (+★) | the trauma shaker: τ², `FRACTAL_NONE` simplex at 14 Hz, the directional kick (ω 28, ζ 0.32), falloff from the focus, fog and frustum gates, ×0.3 precision damping, the §5.4 whitelist | `camera_juice.gd` → `h_offset`, `v_offset` and roll in `_apply()` | — |
| CAM-06 | edge pan that works on every desk (confine Auto; release on focus-out) | `rts_camera.gd` / `cursors.gd` | — |

### 3.15 HUD (24)

| id | P0 scope | file / hook | assets (fallback) |
|---|---|---|---|
| UCA-F1 | `UiJuice` channels (press, nudge, pop, tilt, tint) + the faction `UiMaterial` presets | new `src/ui/ui_juice.gd`, `ui_material.gd`, `theme/kingdom_ui.tres`, `theme/clans_ui.tres` | press and release sounds per material |
| UCA-F5 | HudPulse: three locked tempos (0.5 / 1 / 2 Hz); ≤ 2 pulsing HUD elements | new `src/ui/hud_pulse.gd`; global `hud_pulse` | — |
| HUD-01 | button press and release by material, the command on press, the hotkey echo, hover glow, held targeting, live sub-cards | `command_card.gd`; new `src/ui/card_button.gd` | button press ×2 factions; sub-card flip |
| HUD-02 | tooltips: snappy, docked, live cost colours | new `src/ui/tooltip.gd` | fonts |
| HUD-03 | the cooldown sweep with a clock hand + the ready flash (the chime, ring-out and numerals are P1) | new `src/ui/card_slot.gdshader` | — |
| HUD-05 | availability states (desaturate, hatch, wipe front, lock glyph) | `command_card.gd` per-slot enum; `card_slot.gdshader` | lock glyph |
| HUD-06 | the error line + the shortfall ghost ("−35") | new `src/ui/error_line.gd`; `resource_counter.gd` `show_shortfall()` | — |
| HUD-07 (+★) | faction skin, fonts with tabular figures, the day clock; ★the dusk/dawn clunk (the lit frame, lanterns, golden rim and day tally are P1) | `theme/kingdom.tres`, `theme/clans.tres`; new `src/ui/hud_frame.gdshader`, `src/ui/clock_dial.gd` | Alegreya SC + Alegreya Sans (OFL) in `assets/fonts/`; panel textures; clunk ×2 |
| HUD-08 | selection tiles and bars (ghost bars and the rest are P1) | `hud.gd` `_show_selection`, `_make_icon`, `_set_bar`; new `src/ui/unit_info.gd` | — |
| HUD-09 | production queue slots, honest progress, cancel, full (anticipation and pop-out are P1) | new `src/ui/queue_panel.gd` | queue cancel (a torn slip / an unpicked stitch) |
| HUD-11 | the game menu (the pause sketch is P1) | new `src/ui/pause_menu.gd` | — |
| NTF-01 | AlertRouter (categories, the 8 s throttle, clusters, the quiet on-screen path, fights you started stay quiet); the panned alarm; the advisor at +350 ms; Space (the compass, escalation and the teaching chip are P1) | new `src/ui/alert_router.gd` | alarm ×2 + urgent ×2; advisor lines |
| NTF-02 | minimap pings (shape-coded), jump, scrub, right-click order (marks and hover preview are P1) | `src/ui/minimap.gd` `_draw()` ping list | ping |
| NTF-03 | the clickable message feed + the advisor queue (the slip and tab material and fatigue are P1) | new `src/ui/message_feed.gd` | feed-in ×2 |
| NTF-04 | hero bar buttons (the ribbon and pulse are P1) | `hero_bar.gd` + `UiJuice` | hero icons (rendered once) |
| NTF-05 | the idle-worker button + the `idle_worker` action | new `src/ui/idle_worker_button.gd` | soft tok |
| ECO-12 | the idle-worker button's motion: bounce 1→1.18→1 (260 ms) when the count rises, a glow on the ambient clock after 30 s, α 0.35 at a count of 0 | `idle_worker_button.gd` (the canonical motion) | — |
| ECO-13 | resource odometers: a closed-form roll with the value exact on the event frame; routine gains roll only; `bump(strength, color)` for unusual gains; spend flash; the drain chevron | new `src/ui/resource_counter.gd` | tabular-figure font |
| ECO-14 | denial: the counter SHAKE (6 px, 280 ms, shared by both factions), a red card overlay, a cursor slash, the ghost shakes while placing, the faction error cue + advisor | `hud.gd`, `command_card.gd`, `build_placement.gd` | error cues ×2; advisor denial lines |
| ECO-15 | upkeep tier flip: a card flip + a 3 s label pulse on the warning clock (Appendix A, R9); pitched notes; the teach window (the ruler is P1) | new `src/ui/upkeep_ruler.gd`; `hud.gd` | notched-coin icon; 2 note samples |
| ECO-16 | supply capped (amber + an underline on the warning clock); the completion "+7" / "+10" popup and the cap roll (pending supply and the stalled icon are P1) | `hud.gd`; PopupText | croft and yurt glyphs |
| POR-01 | the 3D portrait viewport: framing, light, a ping-pong cross-fade, paced updates | new `src/ui/portrait.gd` (replaces `_set_portrait_color`) | portrait framing data per unit |
| SEQ-01 | the opening cue + the HUD slide-in; the HUD is live from frame 0 (the swoop is P1) | new `src/ui/start_sequence.gd` | opening cue ×2 factions |
| SEQ-02 (+★) | the end: the UI exits in 300 ms, the stinger at 600 ms, warcries, the banner at 1400 ms, skip; ★the held breath and the 600 ms glide (the dolly, grade and shake are P1; the tableau is P2) | new `src/ui/end_sequence.gd` (the only writer of `Engine.time_scale`) | victory / defeat stingers ×4; warcry lines; a banner brush band per faction; ink spatter |

### 3.16 Audio and music (8)

| id | P0 scope | file / hook | assets (fallback) |
|---|---|---|---|
| UCA-F3 | the `Audio` director: buses from `default_bus_layout.tres`; pools (24 one-shot 3D, 16 loops, 2D polyphonic with our own stealing, Deny, Acks, Advisor, Alarm, Sub); gates; the API incl. `schedule_3d()` and virtual loop voices | `src/autoload/audio.gd` (extended) + new `src/audio/voice_director.gd`, `music_director.gd`, `mix_beds.gd` | an `AudioStreamRandomizer` `.tres` per family (fallback: silent no-op, logged once) |
| AUD-01 | the 17-bus layout + the only duck and filter arbiter (the deepest duck wins; Music ≤ 8 dB down during play) | new `default_bus_layout.tres`; the arbiter in `audio.gd` `_process` (`process_mode` ALWAYS) | — |
| AUD-02 | priorities, pools, caps, battle thinning (importance, the battle bed and the low end are P1) | `audio.gd` gates; `mix_beds.gd` | (P1) battle beds |
| AUD-03 | the ack director: 2D acks on the input frame, debounce, order ticks, punchline protection, the annoyed sequence (5 clicks in 2.5 s), `voice_started` | `voice_director.gd` replaces `play_voice()`; `CommandInput._issue()` → `Audio.order_ack()` | unit VO sets; order ticks ×4 × 2 factions; selection ticks |
| AUD-04 | the listener at the ground focus, following the camera (the muffle and mono are P1) | `audio.gd` `follow_camera()`, called from `RtsCamera._apply()` | — |
| MUS-01 (+★) | rotation with 20–40 s of silence; transitions; ★the night filter (the night pool and hero motifs are P1) | `music_director.gd`; `data/music.json` (`bpm`, `tonic`, `mode`, `first_beat_s`); new `src/audio/music_clock.gd` | 3 tracks per faction with metadata |
| WLD-04 | dusk and dawn stingers whose downbeat lands on T0 | new `src/world/ambience.gd` | `assets/audio/ambience/st_dusk.ogg`, `st_dawn.ogg` |
| WLD-32 | the base bed (the other beds are P1) | `ambience.gd` | `amb_base_kingdom`, `amb_base_clans` |

### 3.17 P0 count per system

| # | system | primary files | P0 rows | of which ★ new rows |
|---|---|---|---|---|
| 3.1 | Fx runtime, time and the event bus | `clock.gd`, `vfx.gd`, `juice.gd`, `unit_pos_tex.gd`, `fx_read.gd`, `fx_warmup.gd`, `events.gd` | 5 | 0 |
| 3.2 | Unit body: composer, animation, locomotion | `unit_view.gd`, `secondary.gd`, `cargo_sway.gd` | 13 | 0 |
| 3.3 | Unit shader and material variants | `unit.gdshader`, `unit_variants.gd` | 3 | 0 |
| 3.4 | Particle and ground primitives | `fx_sprites.gd`, `ground_zones.gd`, `attach_fx.gd`, `school.gd` | 4 | 0 |
| 3.5 | Combat impacts and missiles | `vfx.gd` router, `smears.gd`, `projectile.gd`, `stuck_javelins.gd` | 9 | 1 |
| 3.6 | Orders, selection, cursor and picking | `command_input.gd`, `order_markers.gd`, `selection_circles.gd`, `selection.gd`, `screen_query.gd`, `cursors.gd` | 9 | 0 |
| 3.7 | Floating text and health bars | `popup_text.gd`, `combat_text.gd`, `health_bars.gd` | 2 | 0 |
| 3.8 | Economy and workers | `economy_fx.gd`, `doodads.gd`, `eco_rings.gd`, `mine_fx.gd` | 12 | 4 |
| 3.9 | Buildings | `building_fx.gd`, `build_placement.gd`, structure shaders, `site_parts.gd` | 21 | 0 |
| 3.10 | Heroes | `hero_sigils.gd`, `hero_fx.gd`, `xp_motes.gd`, `hero_bar.gd` | 7 | 0 |
| 3.11 | Spells, statuses, summons and ultimates | `spell_fx.gd`, `status_fx.gd`, `ability_targeting.gd`, `screen_tint.gd` | 20 | 0 |
| 3.12 | Items, loot, shops and creep camps | `loot_fx.gd`, `creep_fx.gd`, `camp_fx.gd` | 9 | 0 |
| 3.13 | World and atmosphere | `atmos.gd`, `day_night.gd`, `world_common.gdshaderinc`, `fog.gd`, `grass.gd`, `water.gdshader` | 22 | 1 |
| 3.14 | Camera | `rts_camera.gd`, `camera_juice.gd` | 7 | 0 |
| 3.15 | HUD | `hud.gd`, `command_card.gd`, `ui_juice.gd`, `hud_pulse.gd`, `alert_router.gd`, `resource_counter.gd`, `minimap.gd`, `portrait.gd`, sequences | 24 | 0 |
| 3.16 | Audio and music | `audio.gd`, `voice_director.gd`, `music_director.gd`, `music_clock.gd`, `ambience.gd` | 8 | 0 |
| | **total** | | **175** | **6** (+ 8 partial promotions) |

---

## 4. Shared infrastructure to build first

Each job has **one owner and one system.** Every domain doc already extends the shared pieces instead of growing its own, and this section pins them down.

### 4.0 Build order

Each wave ends when its moments' clips pass §5.4. No wave starts a row whose infrastructure is missing.

| wave | name | builds | unlocks |
|---|---|---|---|
| 0 | **The spine** (no visible juice yet) | `Clock` autoload; the `Vfx` queue, drain and trace; `Juice` / `JuiceCurves` / `JuicePalette`; `FeelConstants`; `render_order.gd`; UnitPosTex + `sim_time` + `FxRead` (HVF-7); the FND-4 event hooks and the `docs/architecture.md` §5 update; the determinism, framerate and lint tests (G1–G4) | everything |
| 1 | **Primitives** | FxSprites + its packing test (FND-2); PopupText; GroundZones (HVF-2); `unit.gdshader` with the fixed uniform map (CMB-17, HVF-4 base); the governor (FND-3); the Audio director, bus layout, arbiter and voice director (UCA-F3, AUD-01..04); `MusicClock`; CameraJuice (UCA-F2, CAM-05); UiJuice + HudPulse (UCA-F1, F5); ScreenQuery (UCA-F4); warm-up (HVF-6) | every row |
| 2 | **The hand and the blade** | the P0 rows of §3.2 (composer, AnimationTree, locomotion, acks, swing remap, knockback, death), §3.3 (unit shader), §3.5 (impacts and missiles), §3.6 (markers, ripple, paint-in, cursors) and §3.7 (text policy, bars); HUD-01, 02, 03, 05, 06, 08 | SM-01, SM-05 |
| 3 | **The workshop** | worker props and CargoSway (ECO-03); the P0 rows of §3.8 (mines, deposits, the ledger, trees; ECO-21, 22, 27 wait for wave 5) and §3.9 (placement, construction verbs, completion, production, damage, destruction); the economy HUD rows of §3.15 (ECO-12..16), HUD-07, HUD-09 | SM-02, SM-03, SM-04 |
| 4 | **The heroes** | the P0 rows of §3.10 (sigils, XP, level-up, death, revive, altar), §3.11 (SpellFx, StatusFx, targeting, zones, timers, statuses, summons, ultimates) and §3.12 except WLD-07 (loot, shops, creep camps); HVF-5 and HVF-8 from §3.4 | SM-06, SM-07, SM-08, SM-11 |
| 5 | **The world and the frame** | the P0 rows of §3.13 (Atmos, the world include, day/night, the tide, fog, lanterns, grass, water, the Hale Spring); sleeping camps (WLD-07); §3.16 beyond wave 1 (the music director, ambience and stingers); the alert, feed, portrait and sequence rows of §3.15 (NTF-01..05, POR-01, SEQ-01, 02, HUD-11); the camera jumps (CAM-04); the Levy Horn, the gong and the harass alarm (ECO-21, 22, 27) | SM-09, SM-10, SM-12 |

### 4.1 The VFX pool manager (`Vfx` and the pools it routes to)

**`src/fx/vfx.gd` is the router, not a particle system.** Its jobs:
- forward the clocks from `Clock`;
- own the 512-record event ring that sim handlers append to, and drain it at the top of `_process` (FND-4);
- route records to the domain fx modules (`economy_fx`, `building_fx`, `spell_fx`, `hero_fx`, `creep_fx`, `camp_fx`);
- run the governor (FND-3), `allow()` and the 64-sprites-per-frame spawn budget;
- publish `fx_time` / `ui_time` as shader globals; keep the monitors and `trace()`.

Nothing in `_physics_process` spawns, flashes or plays; a debug flag asserts this.

```gdscript
# src/fx/vfx.gd (sketch). Typed arguments only: no Dictionary or Array allocation per event.
func enqueue(kind: int, a_id: int, b_id: int, pos: Vector3, data: Vector4) -> void   # sim handlers only
func allow(kind: int, pos: Vector3, side: int, importance: int) -> bool              # visibility, distance, fog, tier, cap, budget
func spawn(kind: int, p0: Vector3, v0: Vector3, life: float, size0: float, size1: float,
		color: Color, flags: int, seed: float, importance: int) -> void               # one FxSprite
func burst(kind: int, pos: Vector3, n: int, cone: Vector3, importance: int) -> void   # > 16 sprites → ≤ 4 groups, 40–60 ms apart, back-dated t0
func stream_start(region: int, pos: Vector3, period: float, slots: int) -> int        # economy stream regions A–E
func stream_stop(id: int) -> void                                                     # sets t_stop; in-flight puffs finish
func tier() -> int                                                                    # 0 Calm, 1 Busy, 2 Brawl
signal battle_started(pos: Vector3)                                                   # CMB-36
func trace(tag: StringName, entity_id: int = -1) -> void                              # QA (§5.1); a no-op unless --feel-trace
```

**The pools** (one owner each; sizes from the domain docs and Appendix A, R5):

| pool | owner | capacity | eviction / overflow |
|---|---|---|---|
| FxSprites cutout / soft / additive | FND-2 | 1536 / 1024 / 1280 slots; 40 % short-life range (≤ 400 ms) | take the oldest slot of the range; **reject** if it is younger than 50 % of its life (`fx/rejected`) |
| FxSprites importance-3 reserve | heroes §2.3 | 64 cutout / 80 soft / 144 additive, own cursor | when full, take the oldest shared slot held by importance < 3 regardless of age (`fx/evicted_for_imp3`); `fx/rejected_imp3` must stay 0 |
| FxSprites chunks s / m / l | FND-2 | 96 each | capped per destruction at 8 / 16 / 24 |
| FxSprites stream regions A–E | economy §2.3 | 216 / 72 / 24 / 36 cutout, 168 additive | fixed; a stream that cannot get slots does not start (fire falls back to flame cards) |
| SpellFx records | HVF-1 | 48 on a free list | protected classes (zone, ultimate, timer, summon) are never evicted; the list grows by 16 with one warning |
| SpellFx rigs | HVF-1 | 16 pooled nodes, 4 reserved for ultimates | a cosmetic rig is stolen only past 50 % of its life |
| Smears | CMB-20 | 24 (Compatibility 8, low spec 4) | per-cell and per-side thinning (FND-3) |
| Wrecks, falling trees | CMB-30, ECO-11 | 8; 6 (Low 3) | the overflow tree shrink-sinks in its MultiMesh |
| Impact and fire lights | WLD-F4 LightBudget | ≤ 12 `OmniLight3D` on screen (Compatibility: 8 total, ≤ 8 per terrain chunk) | priority spell > impact > fire > house light; the ground-glow sprite stands in |
| Slot MultiMeshes (GroundZones, StatusFx, AttachFx, sigils, emblems, XP, loot, PopupText) | each owner | per doc | **swap-remove compaction**; `visible_instance_count` = the live count (heroes §2.4: degenerate grids above the live range cost +7 ms on llvmpipe) |

**Pool rules** (combat §6 #15, economy §7, heroes §9 #37–40):
- no `Node.new()`, `create_tween()`, Label3D or `OmniLight3D` per effect;
- no per-frame CPU writes for unit-attached instances: positions come from UnitPosTex, and timers from `sim_time`;
- `cast_shadow` OFF and `physics_interpolation_mode` OFF on every fx node (the two nearest falling trees and the listed props excepted);
- `custom_aabb` set to the map bounds on every MultiMesh with vertex motion.

### 4.2 The tween and easing library (`Juice`, `JuiceCurves`, `UiJuice`)

Three layers with one rule: **motion is a closed-form function of age.** No Euler steps, no per-frame `lerp(a, b, k)`, no `TIME`. No Tween ever touches a 3D body. Tweens exist only as UiJuice's one-per-channel HUD tweens and in short scene-level sequences that are not per particle (economy §2.4).

**`Juice`** (`src/fx/juice.gd`, static, allocation-free; combat FND-1, extended by heroes §12 and ui §1):

| group | functions |
|---|---|
| Penner easings | `out_quad`, `in_quad`, `out_cubic`, `in_cubic`, `in_out_sine`, `in_out_cubic`, `out_quart`, `out_quint`, `out_expo`, `out_back(t, c1)`, `in_back(t, c1)`, `out_bounce` |
| springs (exact for any dt) | `spring(x, v, ω, ζ, dt)` (under-, critically and over-damped branches); `spring_track(x, v, a0, a1, ω, ζ, dt)` (first-order hold, ≤ 1 % of a 1 kHz reference at 30 Hz); `kick_for_peak(A, ω, ζ)` = k(ζ)·A·ω |
| **back-out** | `out_back(t, c1)` with c1 from this table only: **1.1** ≈ 4.5 % (TIMBER_SNAP), **1.3** ≈ 6 % (kingdom snaps, crit pops), **1.6** ≈ 9 % (marker pin, standing emblem), **1.70158** ≈ 10 % (UI stamp family only), **2.0** (kingdom clockwork recoil after a snap, 40–50 ms only) |
| **elastic-out** (new, bible) | `ring(t, ω, ζ)` = the spring's step response from rest, 0 → 1 with ringing. **FELT_BOB** = ring(t, 14, 0.35): 2.1 Hz, 2 visible bounces, settled in ≈ 0.8 s. **BRONZE_RING** = ring(t, 28, 0.12): 4.4 Hz, ≥ 3 oscillations, started with its sound. Penner's `out_elastic` is **not** provided: its fixed period ignores mass, aliases at 30 fps and is the "jelly" anti-pattern. `ring` is allowed only on felt, bronze, cloth, and the UI latch family's ring-out; it is banned on stone, on unit bodies and on routine HUD |
| **anticipation** (new, bible) | `anticipate(u, contact, hold, split, hang, pull, c1)`: load, hang, snap, hold, recover. This is CMB-16's `melee_pose` generalised with a `hang` term; with `hang` = 0 it is identical. **`anticipate(contact) == 1.0` exactly**, so a pose always lands on its tick |
| helpers | `damp(a, b, rate, dt)`; `hash01(id, seq, salt)`; `vnoise(id, t, hz ≤ 12)`; `crossed(prev, cur, thr)`; `accumulate(acc, dt, interval)`; `latched(age, peak, decay_ms)` (returns the peak at age 0) |

```gdscript
## One anticipation curve for every strike, swing, cast and final blow (bible §4.2).
## u: phase 0..1 of the whole action; contact: phase of the sim event (damage point ratio, grid point,
## predicted completion, release tick); hold: visual hit-stop after contact (phase units).
## split / hang: shares of the wind-up spent loading / holding the loaded pose; pull ≤ 0; c1: recovery overshoot.
static func anticipate(u: float, contact: float, hold: float, split: float, hang: float, pull: float, c1: float) -> float:
	if u < contact:
		var w := u / contact
		if w < split:
			return pull * out_quad(w / split)                                   # load, settling into the pose
		if w < split + hang:
			return pull                                                         # the hang: a readable beat
		return lerpf(pull, 1.0, in_cubic((w - split - hang) / maxf(1.0 - split - hang, 0.001)))  # snap
	if u < contact + hold:
		return 1.0                                                              # visual hit-stop (sim unaffected)
	return 1.0 - out_back((u - contact - hold) / maxf(1.0 - contact - hold, 0.001), c1)

## Elastic family: closed-form step response from rest (FELT_BOB, BRONZE_RING).
static func ring(t: float, omega: float, zeta: float) -> float:
	return 1.0 + spring(-1.0, 0.0, omega, zeta, t).x
```

**Users of `anticipate`.**

| user | contact | split / hang / pull / c1 | hold |
|---|---|---|---|
| CMB-16 melee swings | `damage_point_ratio` | the combat §4.8 weapon table (slash 0.60 / 0 / −0.30 / 1.3; blunt 0.72 / 0 / −0.45 / 1.6; …) | 40–70 ms; heroes +10; crits 80 |
| ECO-08 chop | the cycle wrap | split ≈ 0.67 and hang ≈ 0.18 of the wind-up (cycle 0.40 / 0.80 / 0.91) | 70 ms; 90 on the felling strike |
| BLD-08 hammer | the grid point | a 120 ms wind-up, `out_quad` load | — (150 ms TIMBER_SNAP recoil) |
| BLD-24 completion | the predicted completion tick | a 450 ms raise to 120°, a hang, a 60 ms strike | ≤ 150 ms if the event is late |
| ABL-01 releases | the release tick (c = 1) | per release class | flick 0, throw 60, raise 80, slam 90, ultimate 110 ms |

**`JuiceCurves`** (`src/fx/juice_curves.gd`; economy §2.4) holds the named material tokens built on `Juice`:

| kind | tokens |
|---|---|
| world motion | TIMBER_SNAP, FELT_BOB, STONE_THUD (no overshoot), BRONZE_RING, CLOTH; SETTLE (by material); CHIRP_SHUDDER (12 → 7 Hz); COIN_SETTLE (precession rising as it dies); SPRING_GLIDE (ω 40, ζ 0.72); the deposit flight solver |
| UI and glyphs only | POP_IN, PUNCH, SHAKE (6 px, 80–100 ms period, 280–300 ms), RISE_FADE, FLARE |

**Every periodic function declares its frequency** (`const FREQ_HZ`), and a test asserts ≤ 12 Hz (economy §9).

**`UiJuice`** (`src/ui/ui_juice.gd`; UCA-F1) runs one tween per channel per control: `press`, `nudge`, `pop`, `tilt`, `tint`. A new tween on a channel kills that channel's old one, and every tween sets `offset_transform_visual_only` and `set_ignore_time_scale(true)`. The helpers read the local faction's `UiMaterial`, so a call site never names a curve: `press`, `release`, `ring_out`, `pop`, `stamp`, `enter`, `leave`, `shake`, `flash`, `catch_light`. **The overshoot budget:** only the latch, stamp and unroll families may overshoot (ui §2).

### 4.3 The material flash helper

**One energy-conserving term everywhere** (CMB-17; economy §2.3):

> f = S · (0.3 + 0.7 · rim), rim = (1 − N·V)²; `ALBEDO *= 1 − 0.6·f`; `EMISSION += tint × 0.45·f`.

Under the noon sun the peak linear luminance stays **≤ 0.95**, below the glow threshold, so units and buildings never bloom (the render readback tests G8).

| caller | API | channel | tints | rules |
|---|---|---|---|---|
| units | `UnitView.flash(strength, tint_id)` | `unit.gdshader` slot 0 `flash` + slot 1 `flash_tint` | hit #FFF6EC → #FF5A48 over 80 ms (heroes 100 ms); death beat #FFF6EC held 60 ms | latched at age 0; a re-hit takes the max; hits under 2 % of max HP flash at 0.5 |
| unit rims | `UnitView.rim(strength)`, `set_rim_boost()` | slot 2 `rim_boost` × slot 7 `rim_col` | hover, select, kill-confirm (team ×1.25), detected, invisible, summon, armour; hero base 0.55, units 0.35, **cap 0.6** | a separate channel from hits, so "selected" and "struck" never share a look |
| buildings | `StructureUniforms.flash(S, tint_id)` | `fxfr` | hit #FFB070; upgrade ripple #FFF1C2; destruction #FFF6EC | **heat gate:** a flash may start at most every 400 ms (≤ 2.5 Hz); S = min(0.6, accumulated heat); latched, decaying over 240 ms |
| HUD | `UiJuice.flash(control, color, ms)`, `catch_light(control)` | `self_modulate` / material light catch | per `UiMaterial` | the UI never uses HDR |

- **Bible ruling (Appendix A, R25):** the unit flash is **written once per event, not per frame**. Slot 0 holds (t0 in `fx_time`, strength, duration, spare), a full-float instance uniform, and the shader evaluates the latched curve. This removes ≈ 2 parameter writes per flashing unit per frame (≈ 400 writes/s in a 200-hits/s brawl) and makes the flash exact at any refresh rate.
- `reduce_flash` halves the strength and drops the white phase, keeping the tint only (combat §2.3).
- The uniform map is fixed with `instance_index(n)` in a shared include (Appendix A, R4), so a variant in `set_surface_override_material` and an overlay in `material_overlay` read the same slots.

### 4.4 The decal-substitute projector

`Decal` is Forward+/Mobile only, so **no `Decal` node exists anywhere.** Five tools cover every ground mark, and every one is draped cliff-exact on `terrain_corners` (HVF-2: the per-tile bilinear, never a filtered height across a wall; α → 0 where a triangle bridges a wall).

| need | tool | owner | cost |
|---|---|---|---|
| a transient flat effect (dust ring, shock ring, ground glow) ≤ 1–2 s | FxSprites with `GROUND_ALIGNED` facing | FND-2 | inside the FxSprites draws |
| a draped area with gameplay (zones, reticles, fills, glyphs, the placement grid, ink blots, packed earth, rubble, dash strips) | **GroundZones patch**: large 32² for zones ≥ 4 m, small 8² below that, glyph 8² | HVF-2 (economy keeps its own MMIs, R8) | 5 draws (heroes) + 2 (economy) |
| an edge, range ring, timer arc or aura pulse | **GroundZones strip**: a 128-segment draped annulus (a 17 m range ring is ~128 thin quads, not a 34 m full-screen quad) | HVF-2 | included above |
| a truthful radius > 11 m around a footprint (levy 22 m, gong 30 m, wide auras) | the **terrain ring list**: 2 `mat4` globals, 4 rings, drawn by `terrain.gdshader` as the footprint dilated by R | economy §2.3 + world | 0 draws, ≈ 12 ALU per live ring per terrain fragment |
| persistent battlefield memory (stains, scorches, scuffs) | the **scar map**: RG8 at 0.5 m per texel, sampled by the terrain shader | CMB-32 (P1) | 0 draws, ≤ 4 uploads/s |

Rules that keep them honest and legible:
- **Truthful radii** within ±2 %, enumerated from the defs by `test_truthful_radii.gd`.
- **Allegiance by edge shape:** smooth for own and allies, notched for hostile, dashed for creeps.
- Fills α ≤ 0.35; the newest overlapping fill keeps 0.35 and older ones drop to 0.15. `GLOAM_DARK` is the one exception, because it darkens rather than covers.
- **Cosmetic rings** ≤ 1.6 m, α ≤ 0.35, no edge line.
- Render priorities and clip-space biases come from `src/fx/render_order.gd` (R3), never literals.

```gdscript
# src/fx/ground_zones.gd (sketch). Times are sim seconds (tick × DT) so the shader compares with sim_time.
func add_patch(mode: int, centre: Vector3, size: Vector2, yaw: float, t0: float, t_end: float, param: float) -> int
func add_strip(mode: int, centre: Vector3, r_in: float, r_out: float, t0: float, t_end: float, param: float) -> int
func remove(id: int) -> void                         # swap-remove; visible_instance_count = live count
# src/fx/eco_rings.gd
func call_ring(hall: Unit, radius_m: float, style: int, owner_pid: int) -> void   # front, hold at R, fade
```

### 4.5 The floating-text system

**PopupText** (`src/fx/popup_text.gd` + `popup_text.gdshader`; economy §2.3) is the only world-text system (R2):
- one MultiMesh of 256 glyph quads: 0–47 reserved for heroes, 48–255 shared by economy and combat;
- an 8 × 8 atlas of 64 px cells, with the fill mask in R and a baked 3 px outline in G;
- a fixed screen size from the projection matrix, with heights given in px at 1080p;
- `render_priority` 110, no depth test;
- motion is closed form on `fx_time` (RISE_FADE), and the CPU writes glyphs only on spawn, merge and digit-roll steps;
- tracked glyphs (≤ 64) store their anchor's UnitPosTex slot, so popups follow a unit walking out of a door at zero per-frame CPU cost.

| rule | value |
|---|---|
| policy | `src/fx/combat_text.gd` decides **what** to show (CMB-28 *Minimal* by default); PopupText decides **how** |
| merge keys | combat (target, kind) within 250 ms; economy (player, kind, drop-off) within 350 ms with a 120 ms digit roll; the camp stamp swallows its bounties (CRP-04) |
| lanes and caps | 2 lanes per anchor (the newer starts 22 px higher); ≤ 6 economy popups on screen (the oldest fades in 150 ms) |
| heights (px at 1080p) | normal 16, heal 18, deposit and bounty 20 (lumber 18), stamp 24 / 20, crit 30, level numeral 34 + a 46 px badge |
| colours (fill / outline) | gold #FFD34D / #4A2E00; lumber #8EDB6A / #1E3A12; heal #7CFF8A; mana #4FA8FF; crit #FF4433; tax #A9B1BA / #22262B; miss #D8D2C8; food #FFF1CF |
| crit pop | 0 → 1.45 in 90 ms (`out_back`), 1.0 by 220 ms, hold to 700 ms, gone by 1000 ms |

**Names** (hero nameplates, hover plates, group numerals) are **2D Labels on the WorldLabels CanvasLayer** (`src/ui/world_labels.gd`; ui §2, SEL-02), placed with `unproject_position()`: pixel-exact, in the HUD font, ≤ 13 labels. **No Label3D is used** (R2).

```gdscript
# src/fx/popup_text.gd (sketch)
func spawn(anchor_slot: int, pos: Vector3, text: String, glyphs: PackedInt32Array, fill: Color, px: float,
		curve: int, merge_key: int) -> int        # anchor_slot = UnitPosTex slot, or -1 for world-anchored
func add_to(id: int, delta: int) -> void           # merge: value += delta, 1.12 bump over 60 ms, life extended
```

### 4.6 The audio event system

**`Audio` becomes a director** (UCA-F3).
- **Gates, in order, on every request:** missing asset → no-op; fog gate; on-screen test (inside the frustum with a 2 m margin, never culled); cull beyond 50 m × d/28; per-id cap and spacing; tier thinning; then allocate or steal by priority (ui §5.2).
- **Acks, UI, alarms and the placement stamp are 2D**, so they start on the input frame.
- **Loops are virtual voices:** they keep their key and position when stolen and come back when a player frees.
- **One arbiter writes bus volumes and filter cutoffs:** keyed ducks, the deepest wins, Music ≤ 8 dB down during play (AUD-01).

**Layered events (bible proposal: `data/sfx_events.json`).** A game event maps to layers, so code calls `Audio.event(id, pos, ctx)` once and the data decides the layering. The domain docs' layer tables (combat §4.8, economy §5, heroes §7, ui §5.3) become entries here.

```json
{
  "melee_hit": {
    "bus": "Combat", "priority": 60, "fog": true,
    "caps": {"per_family": 4, "total": 10, "spacing_ms": 60},
    "layers": [
      {"family": "sw_{weapon}", "gain_db": -10, "align": "peak_on_event", "tier": "brawl:heroes_selected_only"},
      {"family": "hit_{material}_{weight}", "gain_db": -4,
       "pitch": {"base": 1.08, "per_mass": -0.06, "clamp": [0.85, 1.08], "jitter": 0.05}},
      {"family": "hit_sub", "gain_db": -12, "when": "mass >= 2.5", "bus": "Sub"},
      {"family": "hit_solid", "gain_db": -2, "when": "type_mult >= 1.5"},
      {"family": "hit_{material}_h", "gain_db": -1, "when": "flags & KILL", "pitch": {"base": 0.95}, "no_cut_ms": 250}
    ]
  },
  "deposit_gold_kingdom": {
    "bus": "World", "priority": 30, "fog": true, "caps": {"per_player_per_s": 2},
    "layers": [
      {"family": "eco_hod_rattle", "gain_db": -16, "at": "event"},
      {"family": "eco_hatch_coin", "gain_db": -10, "at": "landing"},
      {"family": "eco_settle_tinkle", "gain_db": -18, "at": "first_coin_rest"},
      {"family": "eco_ledger_kingdom", "gain_db": "ledger", "at": "landing", "pitch": "music_clock_note", "pitch_locked": true}
    ]
  }
}
```

| mechanism | rule |
|---|---|
| variation | each family is an `AudioStreamRandomizer` `.tres` (SFX pitch 1.06, ±1.5 dB, no back-to-back repeats; voices pitch 1.0) |
| computed pitch | when an event computes pitch (mass, effectiveness, a `MusicClock` note), the family's random pitch is 1.0 and the jitter comes from `Juice.hash01(entity, seq, salt)`, never double jitter (R20). `pitch_locked` families (risers, ladder bells, ledger, ticks) never jitter |
| timing | `peak_ms` / `peak_s` per sample in `data/sfx_meta.json`. A whoosh or riser starts at event − peak via a crossing test, or with `play(from_position = peak − lead)` when the lead is shorter. Grid-locked sounds use `Audio.schedule_3d(id, pos, at_fx_time)` with `MusicClock.beat_at()` (a ≤ 32-entry list checked each frame) |
| voices | `voice_director.gd`: one ack at a time; What ≤ 1 per 400 ms; Yes and Attack ≤ 1 per 1000 ms; order ticks when debounced; annoyed after 5 clicks in 2.5 s; punchline protection; `voice_started(unit, category, length)` drives CMB-13 and CMB-14, with length 0 when the asset is missing |
| valence | `data/ui_sounds.json` tags every cue `positive` / `neutral` / `negative` / `alarm` / `call`; the review fails any alarm sharing a family with a positive cue (R15) |
| low end | heavy moments get one `Sub` thump (LowPass 140 Hz, panned 0.2 × screen x, ≤ 1 per 250 ms) instead of a shake |

### 4.7 The camera impulse system

**`CameraJuice`** (`src/input/camera_juice.gd`; UCA-F2, CAM-05) is the only thing that moves the camera besides the player's own input. Its results are written to member variables, never allocated per frame.

| element | spec |
|---|---|
| trauma | τ ∈ [0, 1] per channel: combat ≤ 0.35, ability ≤ 0.5, cinematic ≤ 1.0; gameplay total ≤ 0.6. Linear decay: 1.6/s in play, 0.8/s in cinematics |
| shake | s = τ². Translation in the camera plane 0.9 m × (d / 28) at s = 1, so it is constant in pixels at any zoom; roll 1.2°; **no pitch or yaw** |
| noise | `FastNoiseLite` simplex with **`fractal_type = FRACTAL_NONE`** (the 4.7.2 default FBM puts content above Nyquist), sampled by time at 14 Hz (play) or 7 Hz (cinematic), normalised `clamp(n / 0.7, −1, 1)` |
| directional kick ★ | one impulse into a 2D spring (ω 28, ζ 0.32) along −u, where u points from the screen centre to the event; amplitude A = 0.5 m × amount × falloff × (d / 28), v0 = 1.52·A·ω (peak at 47 ms). The view jolts away from the blast, so the shake says where it came from |
| falloff | 1 − smoothstep(r_in, r_out, d_xz) from the camera **focus** (siege 6 / 10 m; slam ultimates 8 / 20 m) |
| gates | in the frustum (2 m margin) **and** visible to the local player; per-source spacing; ×0.3 while a drag box, targeting or placement is active; `Settings.screen_shake`; 0 at juice level 0 and under `reduce_motion` |
| whitelist (exhaustive, ui §5.4) | siege powder +0.35 / pots +0.25 (CMB-27); own slam ultimates +0.40 (ULT-01); a later earthquake class; end-sequence collapse (defeat 0.45, victory 0.30) |
| honesty | picking uses `get_camera_transform()`, which includes the shake offsets, so clicks land on what is on screen; the middle-drag grab uses the unshaken transform |

```gdscript
CameraJuice.add_trauma(&"combat", 0.35, impact_pos)   # the only call site pattern; anything not whitelisted is a review reject
```

**The impulse ladder** (the cheapest honest option first):
1. **The world flinches:** `Atmos.shock(pos, strength)` flattens grass and makes trees lean away (WLD-17; siege 0.5, pot 0.35, crate 0.6, Wagon Ring 0.8, heavy footfalls 0.12).
2. **The ear takes the weight:** a `Sub` thump.
3. **The camera shakes,** whitelisted only.

### 4.8 The feel-constants resource

**`FeelConstants`** (new: `src/fx/feel_constants.gd`, `class_name FeelConstants extends Resource`) holds every global tuning number in one place, so designers tune feel without touching code and tests assert the legal ranges.
- **Files:** `data/feel/feel_default.tres`, plus override resources `feel_competitive.tres` (juice level 0), `feel_cinematic.tres` (level 2), and accessibility overlays for `reduce_motion` and `reduce_flash`.
- **Load and access:** `Vfx` loads the stack at boot into the static `Feel.c`; shader-side values are pushed once as `feel_*` shader globals when they change.
- **Dev builds:** the F9 fx-stats overlay (economy §8) gains a *Feel* tab with sliders and "save as .tres"; the resource hot-reloads with `ResourceLoader.CACHE_MODE_IGNORE`.
- **The rule:** a number in a juice row lives either in the unit's or building's def `fx` block (per entity: mass, motion sheet, material, crown, work loop) or here (global). Never as a literal in fx code. The review rejects literals.

| group | constant | default | legal range | source |
|---|---|---|---|---|
| time | `freq_cap_hz` / `motion_freq_target_hz` | 12 / 7.5 | ≤ 12 / ≤ 7.5 | combat §2.1, heroes rule 8 |
| | `latched_peak_ms`, `min_timed_ms` | 60, 50 | fixed | combat §2.1, economy §2.1 |
| readability | `occlusion_max_ms` | 80 | ≤ 80 | combat §2.2 |
| | `unit_flash_lum_max`, `rim_cap`, `hero_rim`, `unit_rim` | 0.95, 0.6, 0.55, 0.35 | ≤ 0.95, ≤ 0.6 | CMB-17, HVF-4 |
| | `cosmetic_ring_r_max_m`, `cosmetic_ring_alpha_max`, `fill_alpha_max` | 1.6, 0.35, 0.35 | ≤ these | heroes rule 6, HVF-2 |
| | `tell_min_px`, `world_motion_min_px`, `text_min_px` | 4, 1.5, 13 | ≥ these | combat L1, world §2, ui §2 |
| | `body_offset_max_m` (wheeled) | 0.20 (0.30) | ≤ these | combat §2.2 |
| | `ult_tint_alpha`, `ult_tint_inner` | 0.14, 0.55 | ≤ 0.14, ≥ 0.55 | ULT-01 |
| density | Busy enter / exit, Brawl enter / exit (hits per 0.5 s EMA) | 14 / 10, 36 / 28 | — | FND-3 |
| | spark multiplier Calm / Busy / Brawl | 1.0 / 0.6 / 0.35 | — | FND-3 |
| | `spawn_budget_per_frame`, `queue_records`, `queue_wait_ms` | 64, 512, 100 | — | FND-3, FND-4 |
| | `imp3_reserve` (cutout / soft / additive) | 64 / 80 / 144 | ≥ the heroes worst case | heroes §2.4 |
| | `coincidence_scaler` (> 4 hero events in 500 ms) | 0.33 | — | heroes §2.4 |
| motion | `JUICE_G` | 25 m/s² | fixed (R13) | economy §2.4 |
| | `ripple_step_ms`, `ripple_cap_ms`, `ack_min_gap_ms` | 28, 308, 700 | — | CMB-10, CMB-13 |
| | `fidget_tokens_per_s_per_8_idle` | 1 | — | CMB-05 |
| | kingdom snap / recoil; Tormai swell / sway | 40–60 ms / 3–4 % (`out_back` 2.0); 200–420 ms / ω 6–9, ζ 0.25–0.35 | — | heroes rule 14 |
| camera | trauma caps (combat / ability / cinematic / total) | 0.35 / 0.5 / 1.0 / 0.6 | ≤ these | CAM-05 |
| | decay, noise Hz, translation, roll | 1.6/s, 14 Hz, 0.9 m × d/28, 1.2° | noise ≤ 15 Hz | CAM-05 |
| | kick ω / ζ, precision factor | 28 / 0.32, 0.3 | — | CAM-05 |
| | glide T = a + b·log2(1 + D/c) ≤ max | 150, 55, 12, 330 ms | max ≤ 330 | CAM-04 |
| UI | HudPulse tempos, max pulsing | 0.5 / 1 / 2 Hz, 2 | fixed | UCA-F5 |
| | press, shake (A / period / length) | 45 ms; 6 px / 80 ms / 280 ms | shared by both factions | ui §3.1 |
| audio | What / Yes gaps; annoyed threshold | 400 / 1000 ms; 5 clicks in 2500 ms | — | AUD-03 |
| | alert throttle; advisor stale | 8 s; 2.5 s | — | NTF-01 |
| | per-id cap and spacing; pools | 4, 60–100 ms; 24 one-shot, 16 loops | — | ui §5.2 |
| | cull distance; Music duck max in play | 50 m × d/28; 8 dB | ≤ 8 dB | AUD-01 |
| | ledger start / step per minute / floor | −16 dB / −1.5 dB / −26 dB | — | ECO-25 |
| economy | deposit merge, popup cap, glint bucket | 350 ms, 6, 3 per s | — | ECO-04, economy §2.3 |
| | hammer target interval | 650 ms (m ∈ {0.5, 0.75, 1, 1.5, 2} beats) | — | economy §2.7 |
| world | tide speed; night luma units / world | 15 m/s; ≥ 0.60 / 0.35–0.45 × noon | — | WLD-03, world §2 |
| ceremony | XP ≤, level-up, camp cleared, tier-up | 750, 1500 (line 1150), 1600, 1800 ms | ≤ these | heroes rule 3, economy rule 1 |

**Debug-only `generic_mode` flag (P1 QA tool, §5.5).** It replaces every dialect, material token and anticipation with one `out_back(1.70158)` and removes holds and hangs. It exists to render the "AI-slop baseline" for blind A/B reviews; it is never shipped.

### 4.9 The cross-domain frame budget

Mid-range GPU, 1080p, 300 units (≈ 150 on screen), Brawl tier, 60 fps (16.7 ms frame). Every row is a domain doc's own budget; the total is the bible's.

| domain | GDScript CPU avg / peak | draw calls typical / peak | GPU | other |
|---|---|---|---|---|
| combat | ≤ 1.5 ms (with shedding) | ≤ 24 / 40 (the 48 Label3D draws are gone, R2) | — | AnimationTree (C++) ≤ 2.0 ms for 150 skinned units |
| economy and buildings | ≤ 0.6 / 1.2 ms | ≈ 14 / 34 | ≤ 0.6 / 1.5 ms | ≤ 4 economy loops |
| heroes and VFX | ≤ 0.8 / 1.5 ms | ≈ 19 / 36 (+ overlays) | ≤ 1.0 ms | UnitPosTex 24 KB per frame |
| world and atmosphere | ≤ 0.6 / 1.0 ms | ≤ 15 | — | lantern ≤ 4 uploads/s |
| UI, camera and audio | ≤ 0.5 / 0.9 ms | 12 card + ≤ 150 canvas items (batched) | portraits ≈ 0.15 ms per render | ≈ 68 voices worst case |
| **total** | **≤ 4.0 ms average** (+ ≤ 2.0 ms C++ animation) | **≈ 84 typical / ≤ 140 peak** | **economy + heroes ≤ 1.6 ms**; combat and world are measured A/B in their benches (§5.2 G12) | **0 GPU readbacks during play** |

Overload shedding is per domain (combat FND-1, economy §2.8, world WLD-F5 auto-degrade) and always sheds cosmetics, never information.

---

## 5. Feel QA checklist

Feel is verified like gameplay: by scripts that fail the build. Opinions come last, on top of evidence.

### 5.1 The harness

Four layers, each catching what the one before cannot:

1. **Headless unit tests** (`tests/unit/`): maths, determinism, sync, truth, lint. Fast, run on every commit.
2. **Scripted playtests with screenshots** (`tests/playtest/`), under Xvfb on lavapipe (Vulkan) and `opengl3` (Compatibility): look, readability, budgets.
3. **Recorded clips** with Godot's Movie Maker (`--write-movie`, fixed fps): beat timing, refresh-rate parity, audio alignment, occlusion over time.
4. **Human feel review** from those clips and contact sheets (§5.5).

**Making the beat sheets executable: the trace.**
- With `--feel-trace` on the command line, `Vfx.trace(tag, id)` appends `{frame, ui_now, fx_now, sim_tick, tag, id}` to `tests/output/feel/<scenario>.jsonl`. Otherwise it is a no-op that costs one branch.
- Every P0 feature emits its beats with tags named `<feature-id>.<beat>`, e.g. `CMB-08.pin_land`, `HER-04.slam`, `BLD-24.final_blow`.
- Each §2 sheet is transcribed into `tests/playtest/feel/beats/sm_XX.json`: `{"anchor": "HER-04.event", "beats": [{"tag": "HER-04.ratchet", "t_ms": 250, "tol_frames": 1}, …]}`.
- **Tolerance:** ±1 frame at 60 fps for juice-timed beats; +2 frames for beats that wait on a sim tick (the order application can land 0–33 ms after input).

**Test tones.** Audio alignment must be measurable before real assets exist.
- `tools/feel/make_test_tones.py` synthesises one short tone per sound family into `tests/fixtures/tones/`: a distinct pitch, a sharp 2 ms attack, and its peak written into `sfx_meta.json`. These are never shipped.
- `--feel-tones` makes `Audio` load them in place of missing assets.

**Analysis tools** (new, `tools/feel/`; run with `python3 -I`; numpy, PIL and ffmpeg are in the container):

| tool | input | checks |
|---|---|---|
| `beatcheck.py` | trace JSONL + beat file | every listed beat fires once, on its frame ± tolerance, relative to the anchor |
| `framecompare.py` | the same clip at 30 / 60 / 144 fps | frames at shared timestamps (every 1/30 s) match: mean absolute difference ≤ 1.5/255 in the unit, ring and bar ROIs |
| `onsets.py` | the clip's WAV (`ffmpeg -i clip.avi -vn clip.wav`) + trace | each audio onset (5 ms RMS flux) lies within ±1 frame of its trace beat, e.g. a whoosh peak on `CMB-16.contact`, a coin landing on its 16th |
| `occlusion.py` | full frames + a units-only mask pass | health-bar ROIs are never covered; each unit's silhouette is ≥ 60 % unoccluded; no coverage run lasts > 80 ms (5 frames at 60 fps) |
| `luma.py` | frames + masks | unit peak linear luminance ≤ 0.95 (flash readback); night unit luma ≥ 0.60 × noon and world 0.35–0.45 × noon; team chroma ≥ 70 % |
| `tells.py` | trace + `Camera3D.unproject_position` dumps | every semantic tell moves its silhouette extreme ≥ 4 px at 28 m (combat L1) |
| `contact_sheet.py` | clip + beat file | one labelled frame per beat, in a grid, for human review |

**Commands.**

```sh
# 1. headless unit tests (every commit)
godot --headless --path . --import
godot --headless --path . -s tests/run_tests.gd -- --filter=test_juice

# 2. screenshots under Xvfb, lavapipe and Compatibility
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1600x900x24" \
  godot --path . --rendering-driver vulkan --audio-driver Dummy --resolution 1600x900 \
  -s tests/playtest/feel/sm07_level_up.gd -- --shots
xvfb-run -a -s "-screen 0 1600x900x24" godot --path . --rendering-driver opengl3 --audio-driver Dummy \
  --resolution 1600x900 -s tests/playtest/feel/sm07_level_up.gd -- --shots

# 3. clips: Movie Maker forces a fixed fps, so slow software rendering still records exact timing,
#    and the AVI carries the game's own audio mix (MJPEG + PCM)
for fps in 30 60 144; do
  VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1600x900x24" \
    godot --path . --rendering-driver vulkan --resolution 1600x900 \
    --write-movie tests/output/feel/sm07_${fps}.avi --fixed-fps $fps --quit-after $((fps * 4)) \
    -s tests/playtest/feel/sm07_level_up.gd -- --feel-trace --feel-tones
done

# 4. analysis
ffmpeg -loglevel error -i tests/output/feel/sm07_60.avi -vn tests/output/feel/sm07_60.wav
python3 -I tools/feel/beatcheck.py tests/output/feel/sm07_60.jsonl tests/playtest/feel/beats/sm_07.json
python3 -I tools/feel/framecompare.py tests/output/feel/sm07_{30,60,144}.avi
python3 -I tools/feel/onsets.py tests/output/feel/sm07_60.wav tests/output/feel/sm07_60.jsonl
python3 -I tools/feel/contact_sheet.py tests/output/feel/sm07_60.avi tests/playtest/feel/beats/sm_07.json
```

Every scenario is deterministic: a fixed map, seed, spawns and scripted inputs. It drives `World.tick()` and every fx system's `advance(dt)` from scripted deltas where a test needs exact frames (heroes §2.2).

### 5.2 Global gates (every P0 must pass all of them)

| gate | what | how | pass |
|---|---|---|---|
| G1 | **Juice never changes outcomes** | `test_juice_determinism.gd`, extended by economy §9, heroes §10, ui §8 #5 and world §9 #1: the full scenario with juice at level 2 vs `World.visuals = false`, dt from 1/30 to 1/240 s with ±30 % jitter | per-tick hashes of HP, positions, resources, XP, buffs and `world.rng.state` are identical |
| G2 | **Refresh-rate parity** | `test_juice_framerate.gd`, `test_camera_framerate.gd`, `test_atmos_framerate.gd`; clip `framecompare.py` at 30 / 60 / 144 fps | curves exact; springs within 1e-4; trail spawn counts identical and positions within 1 cm; frames at shared timestamps match |
| G3 | **Lint** | new `tests/unit/test_fx_lint.gd` (grep): no `TIME` in juice shaders; no `randf()`, `randi()` or `World.rng` in `src/fx`, `src/ui`, `src/world/atmos*`; no `create_tween()` in `src/fx`; no spawn, flash or play in `_physics_process` (plus a debug assert in `Vfx`); `test_view_reader_lint.gd` keeps `FxRead`, `sim_time` and `Vfx.` out of `src/systems`, `unit.gd` and `src/ai` | 0 hits |
| G4 | **Latched peaks and the frequency cap** | `test_juice_framerate.gd`: with a 30 Hz dt sequence, the rim flash, muzzle flash and glints are each sampled at peak; every periodic `JuiceCurves` function and every rig rotation is ≤ 12 Hz, and above 7.5 Hz shows its spin-disc frame | all |
| G5 | **Sim-tick truth** (rule 4) | `test_swing_pose.gd` (P(dp) = 1, P < 1 before it); `test_spell_sync.gd` (release frame, travel arrival = release frame); deposits on a 16th (economy §9); the BLD-24 final blow on the completion tick; XP chips before the level-up flare (≤ 180 ms) | all |
| G6 | **Truthful radii** | `test_truthful_radii.gd` (enumerated from the defs); `test_eco_rings.gd` (22 m / 30 m `edge_distance`); the cosmetic-ring scan | ±2 %; no def shape without a drawn counterpart; cosmetic rings ≤ 1.6 m, α ≤ 0.35, no edge |
| G7 | **Fog and information honesty** | the fog-leak tests of combat §7 #8, economy §9, heroes §10, world §9 #5 and ui §8 #6, run against the one predicate (R6) | 0 sprites, sounds, labels, glances, shakes, pings, rings, memory texels and stream slots from unseen sources; no enemy XP arc, gem, taste, altar dressing or bearing |
| G8 | **Readability** | `occlusion.py` on every SM clip; `luma.py` flash readbacks (`test_flash_luminance.gd`, the building flash, the sigil bloom scan); the night captures at 00:30, 18:15 and 05:40 | bars never covered; ≤ 80 ms occlusion; units ≤ 0.95 linear; no sigil above 1.0 outside HER-04; night ratios hold |
| G9 | **Legibility** | `tells.py` on the combat tell gallery (`brawl_juice.gd`); the sigil captures at 28 m and 46 m; the world legibility lint | ≥ 4 px semantic tells; every sigil element ≥ its minimum px; world motion ≥ 1.5 px |
| G10 | **Caps and importance** | `test_fx_budget.gd` (economy) and the heroes caps scenario (12 level-ups, 4 ultimates and 2 hero deaths in 500 ms during a 150 v 150 brawl) | every cap holds; `fx/rejected_imp3` = 0; `audio/deny_drops` = 0; no protected record evicted; `visible_instance_count` = live count |
| G11 | **Warm-up** | the first level-up, ultimate, hero death and invisibility of a match after HVF-6 | Forward+: `PIPELINE_COMPILATIONS_DRAW` and `_SPECIALIZATION` deltas = 0; Compatibility: first frame ≤ second + 60 ms (hardware) / + 150 ms (software) |
| G12 | **Performance** | the real-GPU benches: `brawl_juice.gd`, `bench_econ_fx.gd`, `bench_hero_fx.gd`, `bench_atmos.gd`, `hud_states.gd`; in software mode, A/B with each domain's layers off | the §4.9 budgets at 60 fps on the mid-range target; software mode adds ≤ 25 % per domain |
| G13 | **IP** | `python3 tools/ip/check_banned_terms.py data assets tests`; the scoped clans culture lint (economy §10 #14) | 0 hits (no listed term, superseded name or borrowed wording in any id or string) |
| G14 | **Rule 1 latency** (new) | `test_command_latency.gd`: synthetic select and right-click events through `push_input` on 12 units | on the input frame: an Acks or UI voice started, an OrderMarkers instance with t0 = `ui_now`, the rank-0 ring pulse started; the last nod by 308 ms + 1 frame; the first unit's sim position changed within 3 ticks |

### 5.3 Per-system checklist (§3's systems)

| system | must show | automated check | evidence (screenshot / clip) |
|---|---|---|---|
| 3.1 runtime | clocks frozen on pause, scaled by game speed; queue drained only in `_process`; `sim_time` monotonic across pause and resume | G1–G4; `test_view_reader_lint.gd`; a pause-mid-cast test (c < 1 for the whole pause) | monitors `juice/ms`, `fx/queue_depth` logged per second in every bench |
| 3.2 unit body | contact on the tick; mass-scaled springs; no moonwalking; no chorus line | `test_swing_pose.gd`, `test_locomotion_sync.gd` (feet drift ≤ 3 cm), the §4.8 spring table, the spam test (≤ 7 nods per 3 s) | tell gallery captures; a 12-unit ripple capture spanning ≥ 8 frames at 60 fps |
| 3.3 unit shader | no bloom; ebb feet→head; variants per surface | `test_flash_luminance.gd` (Vulkan + `opengl3`); `test_shader_compile.gd` uniform map identical across variants | the flash at peak under noon light; a corpse at +1.4 s |
| 3.4 primitives | packing exact on Compatibility; drape exact at cliffs; compaction | `test_fx_packing.gd` (INSTANCE_CUSTOM 2047 exact, COLOR 3.0, the sign-bit extensions); the drape readback (≤ 2 cm, 100 points near walls) | a GroundZones patch on a cliff edge |
| 3.5 combat impacts | material sparks by arc; smears outside the hull; siege readable from above | the per-side thinning ratio ≤ 10 % apart (`brawl_juice.gd`); the CMB-27 whistle peak on impact (`onsets.py`) | a Pavisier struck from front and back; a bombard shell's shadow mid-flight |
| 3.6 orders and selection | same-frame marks; ripple; shape codes; picking honest under shake | G14; the SEL-03 preview equals the release for 50 random boxes (`test_ui_juice.gd`) | marker family captures; the box with "12 / 17" |
| 3.7 text and bars | *Minimal* policy; merges; ghosts lag but values never do | `test_ui_juice.gd` value = sim on the event frame; popup caps | a 60-unit melee with text on *Minimal* (count the labels) |
| 3.8 economy | deposits on the grid; coins at rest ≥ 300 ms; trees never fall toward the camera; truthful rings | economy §9 (200 deposits × 4 BPM; the coin readback; the rings test); a 50-tree fall-direction test (0 toward the camera when any valid direction exists) | SM-02 and SM-03 clips; a Hodman mid-tip; a levy ring on a cliff |
| 3.9 buildings | strikes lay courses; no healthy site burns; cave-in inside the dust; hysteresis | economy §9 (healthy sites, material swap restore, the plume readability test, the hysteresis pan) | SM-04 clip; a site at 30 % and 92 %; cave-in at +400 ms; burning by day and night |
| 3.10 heroes | find your hero < 0.5 s; XP ≤ 0.75 s; standing emblem reads as a circle; four silhouettes | the heroes §10 XP ceremony, emblem aspect ≥ 0.9, `test_no_rotation.gd` | SM-07 and SM-11 clips; sigil at levels 1 / 5 / 10 at 28 and 46 m |
| 3.11 spells | release on the frame; timers on `sim_time` (also with 300 ms frames); schools by shape | `test_spell_sync.gd`, `test_diegetic_timers.gd`, the colour-blind captures | SM-08 clip; zones own vs hostile; stun with 2 stars |
| 3.12 items and camps | the drop ends on the sim item; "‼" vs "!" on the same frame for the whole camp; the stamp equals the camp total | a CRP-04 sum test (stamp = Σ bounties); a CRP-02 same-frame test | SM-06 clip; loot tiers A–D side by side |
| 3.13 world | one downbeat; night luma; fog concealment within one upload; no `TIME` | `test_time_of_day.gd`, `test_atmos_scroll.gd`, the fog-honesty test, `beatcheck.py` on SM-10 (four downbeat tags within ±1 frame of T0) | the atmos tour captures (06:15 … 00:30) |
| 3.14 camera | firm stops; exact zoom; whitelist only; directional kick | `test_camera_framerate.gd` (the stop clamp < 250 ms; the first frame ≥ 15 % of a notch; the end-stop kick 2.8 % of d) | the SM-08 clip: kick away from the ring |
| 3.15 HUD | the command on press; ≤ 2 pulses in phase; shake shared by both factions; sweeps never reflow | `test_ui_juice.gd` (siblings unchanged; B then H 40 ms apart; HudPulse ≤ 2); `test_alert_router.gd` | `hud_states.gd` captures for both factions |
| 3.16 audio | acks on the input frame; caps; the arbiter alone writes buses; Music ≤ 8 dB down | `test_audio_mixer.gd`; `onsets.py` ack onset ≤ 1 audio buffer after the input frame | SM-01 and SM-09 clips (the alarm's pan: L/R energy ratio toward the alert) |

### 5.4 Signature-moment clip checks

Each moment has a scenario `tests/playtest/feel/smXX_<name>.gd` that stages the anchor deterministically, records clips at 30 / 60 / 144 fps on lavapipe and one at 60 fps on `opengl3`, and saves the contact sheet. `beatcheck.py` asserts the listed beats; everything in the sheet is traced, and these are the ones that fail the build.

| moment | setup | asserted beats (t ms from the anchor) | visual / audio checks |
|---|---|---|---|
| SM-01 | 12 Pavisiers, flat grass; box release then right-click 600 ms later | `SEL-01.pop` 0; `AUD-03.voice` 0; `CMB-08.spawn` 600; `CMB-10.nod` rank 0 at 600 and rank 11 at 908; `CMB-08.pin_land` 760; first `CMB-01.pushoff` ≤ 600 + 100 + 80 | G14; ack onset on the input frame; ≥ 8 frames of ripple |
| SM-02 | 1 Hodman, a Moot Hall, 90 BPM test track | `ECO-04.prewind` −300; `ECO-13.counter` 0; `ECO-04.land` on a 16th note; `ECO-04.coin_rest` ≥ 300 ms before `.coin_erode` | `onsets.py`: the jingle within ±1 frame of the landing and the landing on the music grid; the counter equals the sim on frame 0 |
| SM-03 | 1 Hodman, a 10-lumber oak 3 m in front of the camera | `ECO-08.hold` 0–90; `ECO-20.lookup` 0–180; `ECO-11.fall` 180; `ECO-11.impact` 1080 | the fall direction never toward the camera; the tok pitch at degree 2 (spectral peak); the dust skips a unit standing 1 m away |
| SM-04 | a Drill Yard with a full Hod Chain, 90 BPM | `BLD-24.accel` −1200; `BLD-24.windup` −510; `BLD-24.final_blow` 0 (= the completion tick's frame); `BLD-07K.fwump` 450 | `occlusion.py`: the builder at the wall is never covered > 80 ms; the strikes on the grid before −1200 |
| SM-05 | 6 Grapplers vs 6 Pavisiers | `CMB-16.contact` = the damage tick's frame; `CMB-17.peak` 0; `CMB-21.peak` +55; `CMB-36.clash` 0; then `CMB-30.beat` 0, `.contact` 560, `CMB-31.ebb` 700 | the whoosh peak on contact (`onsets.py`); the rim flash ≤ 0.95; the pavise splinters only from frontal hits (a front and a back hit) |
| SM-06 | the Wheel Marshal + 6 soldiers vs a Sootcoat camp | `CRP-04.stamp` 0; `CRP-04.merge_done` 300; `HER-03.arrive_last` ≤ 750 | the stamp value = Σ bounties; the stinger 2D for the clearing player only |
| SM-07 | the Marshal at 1 XP below level 3 kills a creep | `HER-03.arrive_first` ≤ 180; `HER-04.ratchet` 250; `HER-04.numeral` 250; `HER-04.slam` 820; `HER-04.ladder_bell` 820; `HER-04.line` 1150 | emblem aspect ≥ 0.9 at +300; the ladder bell's pitch = `note(1)` of the track; no shake (trauma log = 0) |
| SM-08 | the Marshal, 8 allies inside 11 m and 2 outside, 4 enemies | `ABL-01.click` −333 / −167 / 0; `ULT-02.rise` 0…120; `ULT-02.call` one per captured unit in 250–850; `ULT-02.handoff_done` 1250 | lock rims on exactly the 8 captured; walk-in allies get none; the kick direction away from the ring centre; the riser peak on release |
| SM-09 | the camera at the army 80 m away; a raider hits a Hodman | `NTF-01.alarm` 0; `NTF-01.advisor` 350; `CAM-04.glide` 600–912; then `ECO-21.ring_front` ≤ 33 → 700; `ECO-21.armed` 1500 | the alarm pan toward the alert (the L/R ratio); one alarm per 8 s on a second hit; the ring radius = 22 m by `edge_distance` |
| SM-10 | the base at 17:58 game time | `WLD-04.downbeat`, `WLD-03.core_focus`, `HUD-07.clunk_tick`, `MUS-01.filter_mid`: all within ±1 frame of T0; `WLD-07.glyph` per camp in 0–6000 | night luma ratios at +1500; no unit tinted by the tide core |
| SM-11 | the Uncut killed by 4 kingdom soldiers | `HER-06.shatter` 0; `HER-06.sting` 300; `HER-06.dissolve` 600–1500; `HER-06.soul_rise` 1500; `HER-07.mourn` = the token's arrival | zero spin on every element attached to her (`test_no_rotation.gd`); the enemy view shows no soul flight |
| SM-12 | the last Shell Hall at 1 HP; a kingdom army attacks | `SEQ-02.ui_gone` ≤ 300; `SEQ-02.stinger` 600; `BLD-16.crack` 800 (real time, fx 350); `SEQ-02.banner` 1400 | `Engine.time_scale` = 1.0 on every tick before `match_ended` (`test_end_sequence.gd`); skip works on every frame |

### 5.5 Human feel review

Every P0 system and every moment is reviewed by at least 3 people from its 60 fps clip at 1×, then at 0.25× (`ffmpeg -i clip.avi -filter:v "setpts=4*PTS" slow.mp4`), with the contact sheet beside it. Each question is scored 0 (fail), 1 (weak) or 2 (good); a moment ships at ≥ 1.5 average and no 0.

| # | question | catches |
|---|---|---|
| Q1 | **Sound off:** can you name the event and its outcome from the picture alone? | audio-only information |
| Q2 | **Picture off:** can you name it from the sound alone? | silent tells; muddy mixes |
| Q3 | **Greyscale + deuteranopia simulation:** is it still readable? | colour-only codes |
| Q4 | At 0.25×, does anything cover a unit, its team colour, ring or bar for more than 5 frames? | occlusion |
| Q5 | Does the hit, landing, strike or downbeat feel *on* the beat: no flam, no early flash, no late thud? | sync errors the tolerance missed |
| Q6 | Would a WC3 veteran recognise the convention, and is every shape, sound and word ours? | weak homage; IP drift |
| Q7 | **Swap test:** move the beat to another unit, hero or faction. Does it still fit unchanged? If yes, it is generic. | slop |
| Q8 | At juice level 0, does every *information* beat survive? | information hidden in cosmetics |

**The blind A/B "slop baseline".** Each moment is also rendered with `FeelConstants.generic_mode` (§4.8). Reviewers watch both, unlabelled, in random order. The real one must be preferred in ≥ 80 % of trials. This is the measurable form of "prove you're better than them".

### 5.6 Definition of done for a P0 row

1. Its numbers live in its def `fx` block or in `FeelConstants`, with no literals in fx code.
2. Its maths has unit tests at 30 / 60 / 144 / 240 Hz where it moves.
3. It emits its trace beats and appears in at least one SM clip or system capture with its beats on time (§5.4).
4. It passes G1–G14.
5. It passes the §5.5 review.
6. Its hooks are in `docs/architecture.md` §5 in the same commit.
7. It runs without art: its fallback is visible in a capture with `assets/` stripped.

---

## Appendix A. Cross-doc rulings

Where the domain docs disagree, this list decides. Each domain doc applies these in its next revision.

| # | topic | ruling | supersedes |
|---|---|---|---|
| R1 | **Clocks** | The `Clock` autoload (`process_priority` −1000, ALWAYS) is the single source of `ui_now` and `fx_now`; `Vfx.now` and `Vfx.ui_now` are read-only forwards. `sim_time` comes from UnitPosTex (HVF-7). `hour` = `DayNight.hour_at(sim_time)`. Any duration the sim owns compares with `sim_time`, never `fx_time`. | combat §2.1 (Vfx-owned clocks) |
| R2 | **Floating text** | PopupText is the only world-text system: combat text, bounty, deposits, hero numerals, stamps. `combat_text.gd` is the policy that feeds it. Bounty uses the deposit look (20 px, coin glyph). Nameplates are 2D Labels on WorldLabels (SEL-02). **No Label3D** anywhere: HER-02's pool of 8 is dropped, HVF-6 warms the HUD font instead, and combat's 48 Label3D draws leave the budget. | CMB-28 (Label3D), HER-02 (Label3D names) |
| R3 | **Render order** | The ×10 table in `src/fx/render_order.gd` (heroes §2.7 + economy row 30) is canonical; combat §2.2's integers migrate. | combat §2.2 |
| R4 | **Unit-shader instance uniforms** | Base 11 at fixed `instance_index` in `src/entities/unit_uniforms.gdshaderinc`: combat 0–4 (`flash`, `flash_tint`, `rim_boost`, `team_sat`, `sat_front`), heroes 5–7 (`status_a`, `status_t`, `rim_col`), economy 8–10 (`prop_sel`, `prop_aux`, `prop_anim`); variant-only 11–12 (DISSOLVE: `dissolve`, `dissolve_col`; DITHER: `invis`, `ghost_col`). The compile test asserts one identical map. | economy §2.3 ("10"; economy at 7–9), heroes §12 (heroes 5–6) |
| R5 | **FxSprites capacity and atlases** | Cutout 1536, soft 1024, additive 1280, chunks 3 × 96; the importance-3 reserve sits inside them. **Each layer binds its own 64-cell atlas** (4 painted 4 × 4 sheets per layer, cells assigned per layer in `data/fx_atlas.json`; a frame used by two layers is duplicated). The packing stays unchanged (cell ≤ 63 + 64 × flags ≤ 2047). This resolves the over-subscribed single atlas (FND-2 25 + economy 16 + heroes 24 + world 7 cells > 64). | FND-2 (one atlas), economy §2.3 sheet numbering, HVF-5 "free cells" |
| R6 | **One visibility predicate** | `Fog.unit_visible(u, pid)` and `Fog.visible_at(pos, pid)` in `src/world/fog.gd` (a stub that returns true until fog lands, with the fog tests skipped and logged). `Vfx.allow`, `ScreenQuery.is_pickable`, `Atmos.visible_at` and every fog gate are thin wrappers. Economy's `FxBudget` is cap data only; its `visible_at` is deleted. | economy §2.1 `FxBudget.visible_at()` |
| R7 | **Facades** | "BallisticFx", "StreamFx" and "GroundFx" in sibling docs mean `Vfx.burst`, `Vfx.stream_start/stop` and GroundZones. `ballistic_fx.gd` is never built. | world §header, economy naming |
| R8 | **GroundZones** | One shader set (HVF-2) with separate `MultiMeshInstance3D`s per owner (heroes, economy), compacted with swap-remove. The shared 96–255 slot partition is withdrawn. | economy §2.3 GroundZones slots |
| R9 | **Pulse tempos** | Every periodic attention cue, HUD or world, runs on HudPulse's 0.5 / 1 / 2 Hz (or an integer multiple of the 2 s ambient period); world pulses do not count toward the 2-element HUD budget. Retuned: ECO-02 oversaturation flicker 3 → 2 Hz; BLD-02 blocker ring 3 → 2 Hz; ECO-15 tick and label 1.5 → 1 Hz; ECO-27 1.5 → 2 Hz; HER-05 Learn sweep every 3 s → 4 s; HUD-01 held targeting 1.4 → 1 Hz. | the listed rows |
| R10 | **HUD sweeps and glints** | Every HUD "gloss" or "glint sweep" (BLD-09, BLD-14, HER-04, HER-05) is `UiJuice.catch_light`. The UI is LDR: HER-01's HDR hero-button glint becomes an additive #FFF4C2 at α 0.8. | those rows |
| R11 | **Toasts** | The BLD-14 toast entrance is `UiJuice.enter` (no overshoot); feed lines live in `message_feed.gd`. | BLD-14 (280 ms BACK/OUT) |
| R12 | **Counter API** | `ResourceCounter.bump(strength, color)`; `punch()` is retired; the CMB-28 coin flight calls `bump(0.5, GOLD_TEXT)` on arrival. | CMB-28 |
| R13 | **Gravity** | `JUICE_G` = 25 m/s² for every object the eye tracks (coins, chunks, props, hats, crowns, gongs, items, stakes, flags, dropped cargo). Particulate sprites ≤ 0.1 m (sparks, droplets, chips, clods, splinters) keep their row's gravity, tuned to their ≤ 400–700 ms lives. | ambiguity between combat §4.8 and economy §2.4 |
| R14 | **Ducks** | The UI's `Audio.duck(key, bus, db, attack_ms, hold_ms, release_ms)` is canonical (heroes' `source` = `key`): the deepest active duck wins, never the sum. A duck tied to a world event (BLD-16's held breath) releases on that event's `fx_time` crossing, not a wall-clock timer, so it holds under game speed and `visual_rate`. | heroes §2.3 signature; BLD-16 "350 ms" |
| R15 | **Valence families** | Positive: the town bell (kingdom); small gong and singing-bowl taps (clans). Alarm: the cheap tower-bell tritone clash (kingdom); the slit drum (clans). Call (player-initiated, neutral): the Levy Horn's low wooden horn; the large door-gong boom of Sound the Gong. Ambience uses none of them. Each is its own sample family, tagged in `data/ui_sounds.json`. | ambiguity between ui §5.3, ECO-22 and WLD-04 ("the clans alarm") |
| R16 | **Buses by name** | The bus contract is by name (`AudioBuses` constants). PortraitVoice is index 15 today; combat's "index 12" is void. | CMB-14 |
| R17 | **Sleep glyph** | A closed-eye glyph, never letters, drawn by the StatusFx head layer (one instance per unit, the §2.6 anchor and min-px rules) and shared with STS-06. Snore rings are an FxSprites soft ring kind, counted by tier (WLD-07). Heroes open question 7 is closed. | WLD-07 "FxSprites head-layer kind"; heroes open question 7 |
| R18 | **Names** | Tattiebogles, Set in Stone, Withy Brute, Hail-Swifts and the Uncut replace the superseded names still used in combat §4.9 (neutrals and clans renames). Her kill style is a straight back-flick, never an orbit (`no_rotation`). The old smoke names are banned terms: use house smoke and `smoke_point`. All ids pass `check_banned_terms.py`. | combat §4.9 names and the Uncut's kill style |
| R19 | **MusicClock defaults** | The first track's `bpm`, `tonic` and `mode` from `data/music.json`; before any track exists, kingdom D mixolydian at 88 BPM and clans D dorian at 92 BPM (both slice themes are on D, heroes §12). Slice tracks stay at 84–100 BPM so every deposit can land on a 16th. | economy §2.7 (kingdom G) |
| R20 | **Audio randomisation** | `AudioStreamRandomizer` families give variation and no repeats. A family whose pitch the event computes sets `random_pitch` 1.0 and takes jitter from `Juice.hash01`, never double jitter. `pitch_locked` families never jitter. | combat §4.8 vs ui UCA-F3 |
| R21 | **Cast points** | 0.3 s by default and 0.5 s for ultimates, as data defaults for slice tuning (heroes open question 1). | — |
| R22 | **Ceremonial lag** | Ceremonial pictures of a discrete change (a badge flip, a lit segment, a stamp, the "+N" pip) may complete within 350 ms of the event; quantities the player acts on are exact on the event frame (rule 2). | ui pillar 4 vs HER-04 |
| R23 | **Staging** | At most one headline element per channel (World, UI, voice) on a moment's downbeat frame; the rest cascade 60–450 ms after it (rule 9). Applied in SM-04: the builder's job-done line follows the fwump. | BLD-09 (all at 0 ms) |
| R24 | **Juice-level defaults** | Text policy *Minimal*; economy popups on at every level (economy open question 17); cooldown numerals off at level 1 and on at level 0 (ui open question 5). Revisit by playtest. | open questions |
| R25 | **Event-written flash** | The unit flash is written once per hit as (t0, strength, duration) in a full-float instance uniform and evaluated in the shader (latched at age 0), never written per frame. Structures keep their CPU heat gate but write only on a gate opening. | CMB-17 ("≤ 2 writes per flashing unit per frame") |

---

## Appendix B. P0 asset manifest

Everything the P0 list needs, by type. **Every item has a procedural or silent fallback**, so the game runs and every test passes without it; QA uses test tones (§5.1). Names are data ids and must pass the IP checker.

**Sound effects** (Seed Audio or CC0; WAV/QOA; families as `AudioStreamRandomizer` `.tres`; `peak_ms`, valence and `pitch_locked` in `data/sfx_meta.json`):

| family group | ids and variant counts | for |
|---|---|---|
| swings | `sw_slash` 6, `sw_blunt` 6, `sw_pierce` 4, `sw_chop` 4, `sw_magic` 4 | CMB-16 |
| impacts | `hit_metal_l/_h`, `hit_wood_l/_h`, `hit_flesh_l/_h` (4 each), `hit_stone` 4, `hit_straw` 4, `hit_crit` 3 | CMB-18, 22, 36 |
| bodies | `fall_light`, `fall_armoured`, `fall_huge` (3 each); pain and death vocals per faction and creep family (6 each) | CMB-30 |
| ranged and siege | `hookgun_fire`, `javelin_throw`, `gust_bolt`, caster bolts, `bombard_fire`, `slingcart_throw`, `shot_whistle` 3, `bullet_hit`, `javelin_hit`, `bombard_hit`, `claypot_hit`, ratchet tick | CMB-24..27 |
| economy | mine creak, door thump, effort huff, felt drag; hod rattle, hatch clack, coin jingle, settle tinkle, felt thup, bag clink, billet clatter; `eco_chop_tok` 3 (at C5), leaf rustle, tree creak, whoosh, crash; "Hup!" / "Hai!" barks; ledger timbres (coin-bell, woodblock, bowl tap, log drum at C5) | ECO-01..25 |
| construction | foundation thoomp, stone toks, wood knocks; chisel tink, mallet tok, felt thup, lattice clack; 1 construction bed per faction; scaffold clatter, fwump, rope creak, crown clunk; gong swell; complete cues ×2 (+ short variants); tier fanfare ×2; town bell; quench hiss + anvil ring; pour + bowl ring | BLD-04..20 |
| damage | heavy thud, fire crackle bed; groan, crack, low boom, rumble, patter, settling creak; cracked bell; cracked gong; felt rip | BLD-15, 16 |
| building voices | `bld_<def>_select` for every slice building and the gold mine (≈ 20) | BLD-18 |
| worker calls | the Levy Horn (2-note wooden horn), chain rattle, hat clank; the door-gong boom + all-clear tap | ECO-21, 22 |
| heroes | level-up cue ×2 factions (on D, 1.4 s); 36 ladder bells; pawl clack; hero-down stings ×2 + enemy hero down; soul whistle; revive swell; deep clank (altar); 8 schools × riser / release / tail; ultimate stingers; wheel rumble, clink, clang, chain loop, bell; fuse hiss; loot chimes ×4 tiers; seal snap, twine pop; recall horn / felt / pigeon; camp stinger ×2; creep startle barks ×3 families | HER, ABL, ULT, ITM, CRP |
| UI kit (ui §5.3) | button press ×2, disabled ×2, error ×2, sub-card flip ×2, selection ticks ×3 × 2, order ticks ×4 × 2, lock-on ×2, cooldown ready ×2, feed in ×2, **alarm ×2 + urgent ×2**, ping, glide whoosh ×2, clock clunk ×2, queue cancel ×2, opening cue ×2, victory and defeat stingers ×4 | UCA, HUD, NTF, SEQ |
| ambience | `st_dusk`, `st_dawn` (downbeat at 1.8 s / 2.0 s), `amb_base_kingdom`, `amb_base_clans` (≥ 45 s loops), `lp_spring`, `lp_wading` | WLD-04, 32, 42, 20 |

**Voice** (ElevenLabs TTS, original scripts, generated before the default voices expire on 31 Dec 2026): 16–20 lines per slice unit (What / Yes / Attack / Ready / Annoyed, job-done for workers); 22–28 per hero plus `levelup_a` ×3, `levelup_5`, `levelup_6`, `levelup_10`, ultimate shouts, 1–2 effort vocals, "need mana"; advisor lines per faction (alerts in "struck / harried / engaged" wording, denials, mine low, completions, research).

**Music:** 3 day tracks per faction (3–4 min, 84–100 BPM) with `bpm`, `tonic`, `mode` and `first_beat_s` in `data/music.json`.

**Textures** (painted, then normalised to the palette; R8 masks where noted):

| texture | spec | for |
|---|---|---|
| FxSprites atlases | 3 layers × 4 painted 4 × 4 sheets (R5): puff, puff2, streak, star, glint4, chip, splinter, shard, droplet, straw, feather, leaf, pebble, clod, mote, ember, smoke, dot, ring, shock-ring, halo, coin (4-frame spin); the economy cells (heap, bag, billet, log pair, felt scrap, flake, tile, shell shard, rope, 3 smoke cut-outs, 3 flame tongues, steam curl); the 24 named hero frames (petal, bract, flame tongue, hail chip/pellet, ivory spoke-chip, bronze fleck, wax-seal chip, 4- and 6-point glints, glyph shard…); the closed-eye glyph and snore ring | FND-2, HVF-5, WLD-07 |
| PopupText atlas | 8 × 8 cells of 64 px: digits, + − % ! ? ×, coin, log, croft, yurt, pick, axe, adze, mallet, gong, notched coin, wheel states, hero cells (up-chevron, XP, wheel badge, gong badge, fist, feather, eye, ×, chalk tally) | §4.5 |
| glyph array | 8 school cast glyphs (512²), sigil faces (wheel, gong, neutral), 8 crack masks, 3 stroke layers; 2 head/feet glyph sheets | HVF-2, 3, 5, HER-01 |
| masks | `brush_mask` 256² R8, `hatch` 64² R8, smear dry-brush stroke 256 × 64, paper grain 128² | HVF-4, CMB-20, BLD-01 |
| world | `atm_noise_tex`, `atm_detail_tex` (256², with FastNoiseLite fallbacks), grass tuft atlas 1024², water stroke normals | WLD-F2, 15, 19 |
| buildings | baked crack, seam and panel masks per material; lattice panel; lamp and window emissive masks | BLD-15, 07C, WLD-05 |
| UI | faction cursors (painted at 256 px, cleaned at 32/48/64 px, fixed hotspots); kingdom and clans panel themes; Alegreya SC + Alegreya Sans (OFL) | CUR-01, HUD-07 |

**Meshes, rigs and parts** (the asset pipeline, `docs/research/ai-asset-pipeline.md`):
- **Workers:** GLBs with prop sub-meshes ≤ 150 vertices each (the hod with its gold heap, billet rows and tile load; the felt bag; the log pair; tools; hats), a `Cargo` bone from the auto-rig, and a `walk_laden` procedural clip.
- **Weapons:** B21 props as separate nodes on hand-bone attachments (falchion, pavise, hand-cannon, flail, javelin, sabre, staff, mirror disc, rake).
- **Heroes:** three braid bones under `Head` (the Uncut); death props (the wheel-shield, the chimney-hat).
- **Building part tags** 0–17 (lintel, door, banner, crown, roof, windows, skirt, hatch, work parts with `CUSTOM0` pivots, stack layers, mark slots); the counting hatch on kingdom drop-offs; the felt door flap on clans halls; crowns per def; T2 hall meshes; flame cards appended at import; walls inset 0.25 m on a 0.2 m apron.
- **Altars and neutrals:** altar parts `FloorWheel`, `Stone1..6`, `GongFrame`; the Weighstall's `Beam`, `PanL`, `PanR`.
- **Rigs and loot:** wagon wheel, crate, kegs and bombard (procedural fallbacks); loot parcel, roll and power-up props; a crow prop.
- **Animation data:** clip markers baked by `tools/bake_clip_markers.gd` (with a mandatory def override for shoot clips).

---

## Appendix C. Where the detail lives

| topic | read |
|---|---|
| springs, the composer, FxSprites packing, the governor, events | combat §3 (FND-1..7), §4.8 tables, §4.9 motion sheets |
| material tokens, the flight solver, MusicClock, PopupText, structure uniforms | economy §2.3–§2.7 |
| `sim_time`, `FxRead`, UnitPosTex, GroundZones, StatusFx, AttachFx, the eight schools | heroes §2, §3 (HVF-1..8), §5 |
| Atmos, the world include, the dusk/dawn beat sheet, LightBudget, WorldMemory | world §2–§5 (WLD-F1..F6) |
| `Clock`, UiJuice and materials, CameraJuice, the bus layout, priorities, the UI sound kit, the shake whitelist | ui §2, §3, §5 |
