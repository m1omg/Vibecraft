# Juice spec: Combat & Unit Feel

*Domain doc of the Vibecraft juice bible. Date: 2026-10-16. Status: design spec, ready to implement.*
*Covers: movement, idle life, order feedback, acknowledgements, attack wind-up and impact, projectiles, combat text, health bars, deaths and corpses, and unit personality.*
*Out of scope (owned by sibling juice docs): hero level-up, revive and hero death banners, spell VFX, building construction, fire and collapse, gold and lumber income popups, creep sleep and camp ambience, camera shake implementation, the HUD frame and the audio mix.*

Inputs: `docs/research/visual-art-direction.md` (VFX are the only things that bloom; chunky saturated painterly look; "toy-soldier" procedural motion), `docs/research/audio-direction.md` (weapon × material matrix; priorities and caps in §3.5), `docs/research/video-references.md` §G (M10 acks, M13 order ping), `docs/research/godot-rts-tech.md` (no `Decal`; MultiMesh everywhere; Compatibility must work) and `docs/architecture.md` (30 Hz sim, physics interpolation, `swing_progress()`, `dead_time()`, `display_pos()`).

---

## 1. Feel goals

Every unit is a **painted tin soldier that answers when spoken to, hits with weight, and falls with dignity**. A one-second clip of a 60-unit melee must show four things at a glance: **where blows land, who is winning, who is in trouble, and who just died.** It must feel *thwacky, not sparkly*. Motion follows a fixed grammar:

- **Anticipation:** a slow pull-back, then a snap.
- **Contact:** a 40–80 ms freeze on the attacker, a white rim flash on the victim, and debris that matches the material struck.
- **Reaction:** a springy wobble, never a ragdoll.
- **Aftermath:** bodies stay, their team colour drains away, and the ground keeps a scar.

WC3 reads well because its effects are **short, chunky and sparse**, and we keep that restraint. Our "juice" goes into **timing curves, secondary motion and readable state tells**, not into particle count.

Pillars:

1. **Every tell is a fact.** Each feedback element reports a real sim event: contact, ownership, order state, danger or death. Nothing flashes "for flavour", and nothing lies. There are no fake blocks or parries, and no resource counts that lag behind the sim.
2. **The click is answered in the same frame.** Markers, ring pulses and head-glances fire on input in real time. The sim then catches up within 1–3 ticks.
3. **Toy-diorama physics.** Squash and stretch, springs and hops. All motion is additive offsets on the visual `body`, never on the sim-owned `Unit` transform.
4. **Readability beats spectacle.** Effects never cover team colour, rings or health bars for more than about 80 ms. Density drops automatically in big fights (FND-3). Colour is never the only code.
5. **Frame-rate proof.** Everything is evaluated from timestamps, closed-form springs or `exp()` damping, so 30, 60, 144 and 240 Hz look identical (verified numerically for the spring in FND-1).

---

## 2. Ground rules (bind every row below)

**Time and determinism**
- The sim is 30 Hz fixed and authoritative. **Juice only reads sim state.** It never calls `World.rng`, never writes `Unit` fields, never changes `Engine.time_scale` and never delays a sim event.
- A "hit-stop" is a hold on the attacker's *visual* pose only (CMB-16). The sim damage tick is unchanged.
- Two clocks live in `Vfx`:
  - `Vfx.now`: real `delta` × game speed, frozen while paused. World effects (sparks, corpses, smears) use it.
  - `Vfx.ui_now`: real, unscaled `delta`. Input feedback (markers, ripples, acks) uses it.
- Transient effects are stored as **start timestamp + duration** and evaluated lazily. An off-screen unit therefore costs nothing and is correct when it comes back. Springs snap to rest while a unit is off-screen.
- Smoothing uses `lerp(a, b, 1 - exp(-rate * dt))`, never `lerp(a, b, k)`. Springs use the closed form in FND-1, never Euler steps.
- Visual randomness comes from a per-unit `RandomNumberGenerator` seeded with `unit.id`, plus `Vfx`'s own jitter RNG. Never `randf()` and never `World.rng`.

**Readability**
- Selection rings and health bars stay on the sim position (`display_pos()`). Knockback and smoothing offsets move only the body, by at most 0.20 m, so picking stays honest.
- Render order: ground marks < rings and markers < units < sparks and smears < health bars (`render_priority` 10) < combat text (`render_priority` 20).
- HDR above 1.0 is allowed only for sparks, flares, motes, muzzle flashes and spell light. Unit flash emission stays at or below 0.6, so units never bloom.
- **Fog of war is honoured.** No sprite, sound, label or look-at is produced at a position the local player cannot currently see, unless the source is the local player's own unit. Invisible units emit nothing visible. The FxSprites shader also samples `fog_tex` as a second guard.
- Colour-blind safety: markers are shape-coded, low HP is shown with hatching, and the enemy target flash has notches.

**Notation**
- Durations are milliseconds at 1× game speed. Distances are metres; the infantry height is 1.6 m and `h` = the unit's height.
- Colours are sRGB hex. "HDR n" means emission multiplier n.
- Easings are Penner functions implemented in `Juice`: `out_quad`, `in_quad`, `in_cubic`, `out_cubic`, `in_out_sine`, `out_back(c1)` (c1 1.70158 overshoots about 10 %, 1.3 about 6 %), `in_back` and `out_bounce`.
- `mass` is `fx.mass` (FND-4).
- Tiers (Calm / Busy / Brawl) and importance levels are defined in FND-3.

---

## 3. Foundations (build first, all P0)

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| FND-1 | **Juice core: clocks, springs, easing, body composer** | every frame per on-screen unit | **Closed-form damped spring** (exact for any dt; see the sketch below). **Damping:** `damp(a,b,rate,dt)`.<br>**Composer:** each UnitView keeps additive layers (`loco, smooth, bank, idle, stance, look, swing, react, ack, wounded`). They are summed into **one** `body.transform` write per frame: `Basis.from_euler(pitch, yaw, roll) * Basis.from_scale(1/√sy, sy, 1/√sy)` (volume preserving), with an offset in unit-local space and the pivot at the feet. No Tween ever touches `body`. | New `src/fx/juice.gd` (`class_name Juice`, static). `unit_view.gd` gets `_compose()`. Units outside the camera frustum (2 m margin) skip composition entirely; test with `Camera3D.is_position_in_frustum()` on `display_pos` and `display_pos + up*h`. | about 3–6 µs per on-screen unit, so ≤ 0.9 ms at 150 on screen | P0 |
| FND-2 | **FxSprites: stateless shader sprite pool** (the workhorse for dust, sparks, chips, motes, smoke, clods, dots and rings) | `Vfx.spawn(kind, …)` from event handlers | Two MultiMeshes: **alpha** (blend_mix, 1536 slots) and **additive** (blend_add, HDR, 1024 slots). Ring buffer; the oldest slot is overwritten. The CPU writes a slot **only at spawn**; the vertex shader computes everything else analytically:<br>`p(t) = p0 + (v0 − g/k)(1 − e^{−kt})/k + (g/k)t` (drag k; plain ballistic when k = 0). Optional ground clamp; size `mix(size0, size1, out_quad(t/life))`; alpha by kind; velocity-aligned stretch for streaks. Expired slots collapse to a degenerate quad. A per-material uniform `now` = `Vfx.now`, so effects freeze on pause and follow game speed. | New `src/fx/fx_sprites.gd` + `fx_sprite.gdshader`. **Packing (verified on Forward+ and Compatibility in a spike, 2026-10-16):** instance basis x = v0, basis y = (t0, life, size0), basis z = (size1, gravity, drag), origin = p0, read via `MODEL_MATRIX` (full float). `INSTANCE_CUSTOM` (half float on Compatibility, still precise enough): r = atlas frame + 16×flags, g = ground_y, b = spin rad/s, a = seed. `COLOR` = start colour (HDR allowed). 4×4 painted atlas: puff, puff2, streak, star, chip, splinter, droplet, mote, ring, smoke, clod, leaf, pebble, dot, shock-ring, spare. One buffer upload per frame when dirty (≈ 200 KB). `custom_aabb` = the map. | 2 draw calls total; CPU about 0.25 µs per spawn; ≈ 10 k verts | P0 |
| FND-3 | **Density governor, LOD, importance, pooled impact lights** | per frame (tier) and per spawn (`allow`) | **Intensity I** = EMA over 0.5 s of on-screen `hit_landed` events per second. **Calm** for I < 14. **Busy** when I ≥ 14 (exit below 10). **Brawl** when I ≥ 36 (exit below 28).<br>**Importance:** 4 = local selected, 3 = any hero, 2 = local unit, 1 = other.<br>`Vfx.allow(kind, pos, importance)` checks frustum, distance from camera focus (near < 28 m, far ≤ 45 m), local-player fog visibility, invisibility, the tier rule for that kind (given in each row) and caps.<br>**Spark multipliers:** Calm 1.0, Busy 0.6 (min 2), Brawl 0.35 (min 1, the flare is always kept). **Never throttled:** rim flash, rings, bars, crit and hero events, death beats.<br>**Impact lights:** 4 pooled `OmniLight3D` (no shadows, range 3–5 m), assigned by priority (hero spell > siege > crit). A full pool steals the oldest of lower priority. Energy ×1.4 at night. | Lives in `src/fx/vfx.gd` (router + governor) and a new `src/fx/impact_lights.gd`. The fog check reads the local player's `Fog` grid; the shader also multiplies by `fog_tex`. | ≤ 0.05 ms/frame; lights cost 4 nodes | P0 |
| FND-4 | **Combat feedback events, fx data, baked clip markers** | sim emits; visuals listen | **New `Events` signals:**<br>• `attack_released(attacker, target, connected: bool)`, from `Unit._release()`. `connected` is false when the target left the range buffer (a whiff).<br>• `hit_landed(target, src, amount, flags: int, type_mult: float)`, from `Combat.hit()` after `take_damage`. Flags: MELEE 1, RANGED 2, SPELL 4, CRIT 8, KILL 16, SPLASH 32, HEAL 64.<br>• `attack_missed(src, target, pos)` (evasion, later).<br>• `projectile_ended(proj, pos, target, hit: bool)`, from `Combat.sim_tick()` before `queue_free`.<br>• `bounty_awarded(player_id, pos, gold, lumber)` (economy).<br>• `Audio.voice_started(unit, category, length_s)`.<br>**New readers:** `Unit.display_facing()` (needs `prev_facing`, mirroring `display_pos()`), `Unit.move_goal()`, `Unit.next_corner()`, `Projectile.progress()` (interpolated 0..1) and `MapData.tex_at(x, z)`.<br>**Def block `fx`:** `{"material": flesh/metal/wood/stone/bone/ethereal, "weapon": slash/chop/blunt/pierce/claw/magic/siege, "mass": 1.0, "gait": biped/quadruped/hover/wheeled/flyer, "corpse": body/none/wreck, "spell_color": "#hex", "anim": {"attack_hit", "attack_end", "death_contact", "walk_plants": [..]}}`. It is a separate block because def `weapon` is already the placeholder-shape hint.<br>**Clip-marker baker:** samples each GLB clip at 120 Hz and writes `data/anim_markers.json`:<br>• attack hit = peak speed of `RightHand`;<br>• attack end = hand speed below 15 % of peak for at least 100 ms;<br>• walk plants = minima of `LeftFoot`/`RightFoot` height;<br>• death contact = `Hips` within 5 % of its final height.<br>Def `fx.anim` overrides the baked values. | `src/autoload/events.gd`, `src/systems/combat.gd`, `src/entities/unit.gd` (two lines in `_release`, `prev_facing` in `sim_tick`), `src/autoload/defs.gd` (defaults: material flesh, weapon slash, mass 1, gait biped, corpse body). New `tools/bake_clip_markers.gd` (headless). Whoever lands this updates `docs/architecture.md` §5 in the same commit. **Infantry GLB facts:** bones `Head`, `neck`, `RightHand`, `LeftFoot`, `RightFoot`, `Hips`; clips attack 1.5 s, death 2.97 s, idle 4.0 s, walk 4.13 s; the weapon is not a separate node. | signals about 1 µs each; at about 200 hits/s that is negligible | P0 |

**FND-1 sketch (load-bearing; verified frame-rate independent at 30/60/144/240 Hz and jittered dt, identical to 6 decimals):**

```gdscript
# src/fx/juice.gd — visual only. x = offset from rest, v = velocity. Exact for any dt.
static func spring(x: float, v: float, omega: float, zeta: float, dt: float) -> Vector2:
	if zeta < 1.0:
		var wd := omega * sqrt(1.0 - zeta * zeta)
		var e := exp(-zeta * omega * dt)
		var c := cos(wd * dt)
		var s := sin(wd * dt)
		return Vector2(e * (x * c + (v + zeta * omega * x) / wd * s),
			e * (v * c - (omega * omega * x + zeta * omega * v) / wd * s))
	var e1 := exp(-omega * dt)
	var b := v + omega * x
	return Vector2((x + b * dt) * e1, (v - omega * b * dt) * e1)

static func damp(a: float, b: float, rate: float, dt: float) -> float:
	return lerpf(a, b, 1.0 - exp(-rate * dt))
```

Impulse rule: with ζ = 0.32, a velocity kick `v0 = 1.52 × A × ω` peaks at offset A after 1.31/ω s. For ω = 24 that is 55 ms, and the wobble settles below 5 mm at about 450 ms.

---

## 4. Feature table

★ = our own twist (see §5). Rows reference FND ids for the plumbing.

### 4.1 Movement and idle life

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| CMB-01 | **Start push-off, stop plant, arrival settle** (+ formation slot sparks) | gait change from CMB-03 (idle→walk, walk→idle); group move order | **Start:** pitch to +9° forward in 90 ms (`out_quad`), then spring (ω 12, ζ 0.5) to a cruise lean of +5°. The first footstep's dust is ×1.5.<br>**Stop:** pitch to −5° in 70 ms, then spring back to 0 (ω 14, ζ 0.4: one visible overshoot). Squash sy 0.96→1.0 over 120 ms. 2 dust sprites at the feet.<br>**Stride amplitude** follows speed via `damp(rate 9/s)` (≈ 150 ms to 75 %).<br>**Slot sparks (P2):** one tick after a group move, each unit's formation goal shows a 0.12 m dot #57E36A α 0.6 for 600 ms (fading over the last 200 ms), so the player sees the formation's shape. | `unit_view.gd` layer `loco`, reading `velocity` and the CMB-03 gait state. GLB units: lean applied on `body` (the GLB root), never on bones. Slot sparks use `Unit.move_goal()` → FxSprites kind `dot`. | ~1 µs/unit; 0 draws | P0 (slot sparks P2) |
| CMB-02 | **Banking into turns + head-lead** | turning while moving; upcoming path corner | **Yaw rate** ω_y = wrapped Δ`display_facing()`/dt, smoothed with `damp` at 20/s.<br>**Roll** = clamp(−ω_y × speed_ratio × k, ±max), through a spring (ω 10, ζ 0.7):<br>• biped: k 0.07, max 10°;<br>• quadruped/cavalry: k 0.10, max 14°;<br>• hover: k 0.12, max 18°;<br>• flyer: k 0.18, max 28°, plus nose-down 6° above 0.8 speed;<br>• wheeled: k 0, with a 3° outward body roll instead (suspension).<br>**Reversal** (> 120° within 0.25 s): pivot squash sy 0.97 for 70 ms + 1 dust sprite.<br>**Head-lead:** the head looks at the next path corner once it is within 3 m, so the head turns about 150 ms before the body. | Layer `bank`. Head: `LookAtModifier3D` on `Skeleton3D` (bone `Head`, fallback `neck`; `duration` 0.15, TRANS_SINE, angle limit 70°), with a target Node3D moved at 10 Hz from `Unit.next_corner()`; `influence` 0 when > 30 m away or off-screen. Placeholders pre-yaw the body by 30 % of the upcoming corner angle (≤ 12°). | bank ~0.5 µs/unit; LookAt ~3–5 µs per near skeletal unit | P0 bank / P1 head-lead |
| CMB-03 | **Crowd anti-jitter** (separation without twitching) | always, mobile units | Separation steering shoves units by centimetres per tick, so walk/idle flicker and the shuffle must be hidden.<br>**Gait hysteresis:** enter walk at speed_ratio > 0.35 held for 80 ms; return to idle below 0.12 held for 120 ms. In between is *shuffle*: bob at 30 % amplitude, stride frequency at 60 %, no dust.<br>**Position low-pass:** while speed < 0.8 m/s (or holding/swinging), `vis` follows `display_pos()` through a spring (ω 14, ζ 1; ω 25 while swinging). Otherwise it blends to pass-through over 150 ms. The body offset `vis − display_pos` is clamped to 0.20 m.<br>**Yaw dead-zone:** below 0.8 m/s, ignore facing changes under 8°; otherwise `damp` at 18/s. | Layer `smooth`. Clip units: crossfade 0.18 s between idle and walk; shuffle = walk at `speed_scale` 0.5 blended at 0.35 weight (AnimationTree Blend2), or idle when there is no tree. Rings and bars stay on the sim position. | ~1 µs/unit | P0 |
| CMB-04 | **Footstep dust by terrain** | foot plant: procedural stride phase crossing 0/π; clip = baked `walk_plants` | **Sprites per plant:** biped 1 (heroes and mass ≥ 2.5: 2), quadruped 2, mass ≥ 2.5: 3 at ×1.6 size, hover: a soft ring every 0.4 s, flyer: none.<br>**Puff:** size 0.18→0.5 m, α 0.35→0, life 450 ms, v = −move_dir × 0.35 + up 0.25 m/s, drag 2.<br>**Colour by `MapData.tex_at` at the foot:**<br>• grass: 2 leaf flecks #8FA45A (0.06 m, hop 0.15 m, gravity 6) plus a faint puff #A8A878 α 0.2;<br>• dark grass: flecks #6E8A3E;<br>• dirt: #A98E62;<br>• rough dirt: #94795A;<br>• rock: 2 pebble ticks #8E877C, no puff;<br>• sand: #D1B583 at ×1.3;<br>• dry grass: #B8A26A;<br>• paved: #9A8F7C α 0.2;<br>• shallow water: splash ring #CFE8F0 0.4 m + 3 droplets.<br>**Tier:** Busy keeps only importance ≥ 3 and mass ≥ 2.5; Brawl turns it off. Sub-cap 192 live dust sprites; near LOD only (< 28 m). | `unit_view.gd` calls `Vfx.footstep(pos, dir, size_class)` → FxSprites alpha. Per-unit footstep audio is not used (audio doc), except hero thumps (CMB-34). | ≤ 300 spawns/s worst case ≈ 0.1 ms/frame | P1 |
| CMB-05 | **Idle life: desynced breathing, fidget pool, guard ring ★** | idle (no order, not swinging, gait idle) | **Breathing:** period 2.8 s × r with r in [0.85, 1.15] from the per-unit RNG, random phase. Amplitude sy 2.5 % (worker 2 %, mass ≥ 2.5: 3.5 %). Period ×1.15 at night.<br>**Fidgets:** each unit fidgets every 7–15 s. A global token bucket allows ≤ 1 fidget start per second per 8 on-screen idle units, so there is never a chorus line. Pool:<br>• weight shift (roll ±3°, 900 ms `in_out_sine`);<br>• look-around (head or body yaw ±30° over 1.4 s);<br>• stretch (sy 1.04, 700 ms);<br>• weapon check (swing pose 0.1, 300 ms);<br>• worker tool-to-shoulder (pitch +4°, 600 ms);<br>• yawn, 18:00–06:00 only (sy 1.05, pitch −6°, 900 ms).<br>**Guard ring ★:** when ≥ 4 own units idle within 6 m after a move completes, each turns its visual body to face outward from the group centroid, limited to ±60° from its arrival facing. The turn takes 600–900 ms, staggered. The offset collapses in 120 ms on any order, acquisition or swing. | Layer `idle`; token bucket in `Vfx`. Clip units play `fidget_*` one-shots when the GLB has them (`AnimationNodeOneShot`); otherwise the motion is procedural on `body`. | ~0.5 µs/unit | P1 (desynced breathing P0) |
| CMB-06 | **Look-at and "notice" layer** | combat target; order click; enemy approach; idle | **Priorities:**<br>1. Swing or combat target.<br>2. **Order glance:** on the click (ui time), every selected unit's head snaps toward the marker in 80 ms and holds 400 ms. This happens *before* the sim moves the unit, covering the ≤ 33 ms tick and path-budget delays.<br>3. **Notice:** the nearest enemy visible to the local player within acquire_range × 1.5, re-checked every 250 ms with id-staggered scans. A **creep camp alerts as a group**: heads come up (pitch −5°), breathing runs ×1.6 and fidgets stop. They relax 2 s after the intruder leaves, which telegraphs aggro range while you creep.<br>4. Idle glance at an ally within 6 m every 5–9 s, for 1.2 s.<br>**Limits:** head yaw ±70°, pitch ±20°, `damp` 10/s. Invisible or fogged enemies are never noticed (no information leak). | `LookAtModifier3D` (as CMB-02) with a per-unit target node; placeholders use a body-yaw offset only (≤ 12°). The notice scan calls `World.query_radius` read-only into a Vfx-owned array. | scan amortised ≈ 0.05 ms/frame; LookAt as CMB-02 | P1 |
| CMB-07 | **Stance tells ★** (order state readable on the battlefield) | `unit.current.type`, `holding`, engaged between swings | Transitions take 250 ms (`in_out_sine`).<br>**Hold:** crouch (body y −0.04 h, pitch +4°), weapon/shield pose 0.25 forward, fidgets off, breathing ×0.8: a planted line.<br>**Attack-move or patrol advancing:** weapon pose 0.15 raised, extra lean +4°, stride ×1.05.<br>**Patrol:** head scans yaw ±35° as a sine at 0.25 Hz.<br>**Plain move:** relaxed, weapon at 0.<br>**Engaged between swings** (target set, cooldown running): combat idle with weapon 0.1 and breathing ×1.4, so fighters never look relaxed. | Layer `stance`. Clip units: body crouch/pitch in the slice; later an additive spine offset through a custom `SkeletonModifier3D` (P2). | negligible | P1 |

### 4.2 Orders and acknowledgement

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| CMB-08 | **Order markers, shape-coded** | `CommandInput` click: same frame as the input, before the tick | **Move** (circle family; #57E36A with outline #0E2A12 α 0.6):<br>• 3 ripple rings, r 0.25→R where R = clamp(1.0 + 0.25√n, 1.0, 2.2) and n = selection size; 420 ms `out_cubic`, staggered 70 ms; α 0.95→0 (`in_quad`); thickness 0.06→0.02 m.<br>• Pin: a chunky downward chevron (0.35 m) drops from +0.9 m to +0.15 m in 160 ms (`out_back` 1.6), holds to 450 ms, then shrinks over 180 ms (`in_back`). 3 terrain-coloured dust sprites on landing.<br>**Attack-move** (chevron family, #FF5A36): 4 inward chevrons converge from r 1.2 to 0.35 m in 260 ms (`in_quad`), then a ring flash (r 0.9, 120 ms) and a 200 ms fade.<br>**Patrol** (#FFC93C): two curved arrows chase each other 180° around a 0.8 m circle over 600 ms.<br>**Attack-ground** (#FF5A36): a 1.2 m crosshair ring whose 4 ticks slide in over 200 ms.<br>**Shift-queued:** the pin carries the waypoint index digit (1–9); only the first ring ripples. | New `src/fx/order_markers.gd`: a pool of 8 (quad + chevron meshes) on `ring.gdshader` extended with `notches` and `progress`. It **replaces `CommandInput._marker()`**, which today allocates a mesh and material per click. Tweens use real time (`TWEEN_PROCESS_IDLE`). Sounds are owned by the UI/audio doc. | ≤ 8 draws while visible | P0 |
| CMB-09 | **Target flash** | smart/attack/follow/gather on an entity or tree | A temporary ring appears around the target (selected or not) at its ring radius and blinks 3 times: on 0–80, off 80–150, on 150–230, off 230–300, on 300–380, fading 380–460 ms.<br>**Colours:**<br>• enemy (attack): #FF5A36 **with 4 notches** (12° gaps), the colour-blind shape code;<br>• ally (follow): #FFE066, plain;<br>• gold mine: #FFD34D;<br>• tree: #9BD56B.<br>**Body:** one rim pulse (`rim_boost` 1→0 over 140 ms, same tint).<br>**Trees answer:** the doodad's chop-shake (±3°, 2 cycles, 300 ms). | `selection_circles.gd` gains a transient list (unit or pos, colour, notches, t0); the notch count is encoded in instance alpha; `doodads.gd shake(tree)`. | trivial | P0 |
| CMB-10 | **Order ripple through the selection ★** | any order to ≥ 2 selected units | Each unit's delay = min(16 ms × d, 260 ms), where d = its distance from the selected unit nearest the click.<br>**Ring pulse:** radius ×1.0→1.22 in 60 ms (`out_quad`), back to 1.0 in 120 ms (`in_out_sine`). The ring tints to the order colour (CMB-08) at the peak and returns to its relation colour over 180 ms.<br>**Body nod:** pitch +4° in 50 ms, back to 0 in 110 ms.<br>The speaking unit does CMB-13 instead. A wave of obedience runs through the army, so units that start moving a few ticks late (path budget) have visibly "heard" the order. | Per-unit pulse map in `selection_circles.gd`; composer layer `ack`; `Vfx.ui_now` timestamps. | trivial | P0 |
| CMB-11 | **Shift waypoint lines** | Shift held with own units selected; also for 1.2 s after any shift-queued order | **Paths:** one line per unit when ≤ 4 are selected, otherwise one line from the group centroid. Each runs pos → current goal → queued goals.<br>**Dashes:** 0.35 m dash, 0.25 m gap, 0.09 m wide, draped on terrain (sampled every 0.5 m, +0.07 m), flowing toward the goal at 1.6 m/s, α 0.75, coloured by order type (CMB-08).<br>**Waypoints:** a 0.3 m ring with the index digit at each one. A patrol's return leg is drawn thinner.<br>**Fades:** in over 120 ms on Shift down, out over 250 ms on release.<br>**Caps:** 12 lines, 256 dashes. | New `src/fx/waypoint_lines.gd`: a MultiMesh of dash quads (shader flow `UV.x + now × 1.6 / 0.6`), rebuilt at 15 Hz only while visible, reading `unit.orders` read-only. | ~0.1 ms per rebuild; 1 draw | P1 |
| CMB-12 | **Rally flag and rally line** | rally set on a production building; that building selected | **Flag:** pole 1.6 m #E8DFC8; cloth 0.5 × 0.35 m in team colour.<br>**On set:** the flag drops from +1.4 m (`out_bounce`, 300 ms) with 4 dust sprites and a "plant" thunk.<br>**Cloth wave:** vertex offset 0.05 m × uv.x × sin(6 uv.x − 5t).<br>**Rally line:** dashed (CMB-11 style), #F2E9D8 α 0.6, from the building's edge to the flag, flowing toward the flag.<br>**Rally on a unit or mine:** a 0.6× mini-flag bobs above the target and follows `display_pos`.<br>**Alt held:** all own rally flags show at α 0.35, without lines. | New `src/fx/rally_flags.gd`: pool of 4 (MeshInstance3D + cloth ShaderMaterial), reading `rally_pos` / `rally_id`. | ≤ 4 draws | P1 |
| CMB-13 | **Acknowledgement hop + speaker shimmer** | `Audio.voice_started(unit, category, len)`; with no voice asset, the first selected unit on order/select | **yes/attack hop:**<br>• 0–60 ms: sy 1→0.90 (`out_quad`), an anticipation squash.<br>• 60–130 ms: sy →1.08 and lift 0→0.07 m × h/1.6 (`out_quad`).<br>• 130–230 ms: sy →1.0, lift →0 (`in_quad`).<br>• 230–290 ms: landing squash 0.97→1.0 (`out_back`). sxz = 1/√sy.<br>**attack** also brandishes: weapon pose +0.15 for 200 ms.<br>**what** (select): an attentive look-up, pitch −6° in 100 ms, spring back (ω 12, ζ 0.5).<br>**Speaker shimmer:** the speaker's ring goes to α 1.0 and +30 % width for the line's length, fading 150 ms after.<br>Deferred to the end of a backswing; never on a corpse. | Layer `ack`; `Audio` emits `voice_started`; shimmer lives in `selection_circles.gd`. | trivial | P0 |
| CMB-14 | **Portrait talk (voice-driven)** | a voice line playing for the portrait unit | **Envelope** e from `AudioServer.get_bus_peak_volume_left_db(Voice)`, converted dB→linear; attack 15 ms, release 90 ms (separate `damp` rates).<br>**3D portrait:** `Head` pitch = e × 10° (our rigs have no jaw). Syllable nod: when e rises past 0.55 after being below 0.3, add pitch +4° through a spring (ω 18, ζ 0.5). Idle portraits breathe and look around (CMB-05 timings).<br>**2D placeholder:** the initials panel scales by 1 + 0.06e, with a 3-bar speech glyph driven by e.<br>**Annoyed lines:** the portrait leans in (scale 1.08). | Driver lives in `hud.gd`; the portrait SubViewport itself is owned by the UI doc. | 1 bus read/frame | P1 |
| CMB-15 | **Fourth-wall glance ★** (annoyed clicks) | `Audio` escalates to `annoyed` | The speaker turns its visual body toward the camera: yaw to the camera's XZ position, clamped to ±75°, over 220 ms (`in_out_sine`). It shakes its head ±8° at 3.5 Hz for the first 500 ms, holds for the line (≤ 6 s), then turns back over 300 ms.<br>Skipped while moving or swinging; the portrait still reacts.<br>Heroes "cross their arms" instead: sy 1.03 + pitch −4°. | Layer `ack` (yaw offset); camera from `get_viewport().get_camera_3d()`. | trivial | P1 |

### 4.3 Attack, impact and reaction

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| CMB-16 | **Swing remap: anticipation, snap, attacker hit-stop** | `unit.swing_progress() ≥ 0` | **Inputs:** s = `swing_progress()`, dp = `damage_point_ratio()`, T = (damage_point_ticks + backswing_ticks) × DT.<br>**Hit-stop hs:** 40 ms (pierce, workers), 55 ms (mass ≥ 2.5, blunt, chop), 60 ms (heroes), 80 ms (crit). h = min(hs/T, 0.35(1 − dp)).<br>**Melee pose P** (sketch below):<br>• wind-up u = s/dp: pull back to −0.30 over the first 62 % (`out_quad`, decelerating into the loaded pose), then snap to +1.0 (`in_cubic`);<br>• **P = 1.0 exactly for dp ≤ s < dp + h** (mass ≥ 2.5 adds an attacker squash sy 0.96);<br>• recovery r → P = 1 − `out_back(r, 1.3)` (≈ 6 % dip past rest).<br>Placeholder mapping: pitch = −0.5P, z = −0.22 P h.<br>**Clip units:** `callback_mode_process = MANUAL`, `seek(t, true)` every frame:<br>• t = hit × W(u), where W = 0.45 × `in_out_sine`(u/0.62) up to u = 0.62, then `lerp`(0.45, 1, `in_quad`);<br>• hold t = hit during h;<br>• then t = `lerp`(hit, end, r).<br>Playback rate is clamped to 0.5–2.0× (log a warning otherwise).<br>**Whiff** (`connected = false`): same curve, h = 0, smear only.<br>**Heavy-hit telegraph (P2):** for mass ≥ 2.5 attackers, during the last 300 ms of wind-up a dust ring converges at the target's feet (r 1.0→0.3 m, α 0→0.45, #B3A48C). | Replaces `UnitView._animate_swing()`. Clip `hit`/`end` come from FND-4. The **whoosh** fires at u = 0.62. The contact pose lands on the sim damage tick *by construction*: P(dp) = 1, and P < 1 before it. | ~1 µs per swinging unit | P0 |
| CMB-17 | **Victim rim flash** (white → warm red, 80 ms) | `hit_landed` on a unit | **Timeline:** 0–30 ms flash 1.0, tint #FFF6EC; 30–80 ms flash →0 (`out_quad`) while the tint moves to #FF5A48.<br>Hero victims: 100 ms total. Hits under 2 % of max HP: intensity 0.5. A re-hit takes the max.<br>**Shader:** f = flash × (0.3 + 0.7·rim), rim = (1 − N·V)². ALBEDO = mix(albedo, tint, 0.6f); EMISSION += tint × 0.6f. The silhouette pops but team colour still reads, and the result stays under the glow threshold.<br>**Structures:** no white flash; a 60 ms value dip ×0.85 plus chips (CMB-18). | New **`src/entities/unit.gdshader`** uber-shader for GLB units: team mask plus instance uniforms `flash`, `flash_tint`, `rim_boost`, `team_sat`, `sat_front`, `dissolve`. Instance uniforms were **verified on Forward+ and Compatibility** in a spike (2026-10-16). The placeholder shader gains the same uniforms. Parameters are written only while active. | ≤ 2 `set_instance_shader_parameter` per flashing unit per frame | P0 |
| CMB-18 | **Material × weapon hit sparks** | `hit_landed`. Contact point: melee = victim.pos + dir_to_attacker × victim.radius × 0.9, at y = top × 0.55; ranged = projectile end position | Uses the matrix in §4.8. The emission cone is centred on the reflection of the attack direction, flattened and biased 25° up.<br>**Life:** ≤ 400 ms (chips and clods ≤ 700 ms).<br>**Count** = base × weapon mult × tier mult × effectiveness mult (CMB-19), minimum 1.<br>**Gore setting:** Stylized (default) or Off; Off swaps flesh droplets for dust #D9CBB0. | `vfx.gd` router → FxSprites (alpha + additive), driven by data `fx.material` and `fx.weapon`. | ~6 sprites per hit; at 200 hits/s ≈ 0.3 ms/frame of buffer writes | P0 (flesh, metal, wood, stone) / P1 (bone, ethereal) |
| CMB-19 | **Effectiveness tell ★** (the counter chart, felt) | `hit_landed.type_mult` (attack type × armor type) | **≥ 1.5, "solid":** sparks ×1.4 count and ×1.25 size, full flash, impact sound plus a "crack" sweetener at +2 dB.<br>**≤ 0.5, "glancing":** sparks ×0.6 with colours lerped 50 % toward #9A9A9A, the cone deflected 50° sideways, flash 0.5. The sound becomes a "tink" (metal/stone) or a dull "thud" (others) instead of the normal impact.<br>Anything between is normal.<br>Never uses text, and never colour alone: size, brightness and sound all carry the cue. | `vfx.gd` router only. | 0 extra | P1 |
| CMB-20 | **Painted swing smears ★** | melee swing from u = 0.85 through the contact hold (also whiffs) | **Mesh:** one arc, a 100° sector with inner r 0.35 and outer r = reach + 0.4 m, scaled by h, at chest height and oriented by facing.<br>**Shape by weapon:**<br>• slash: diagonal 35°;<br>• chop: vertical 80°;<br>• blunt: overhead 60°, a shorter (70°) and thicker arc;<br>• claw: 3 thin parallel arcs;<br>• pierce: a straight thrust streak.<br>**Texture:** a hand-painted dry-brush stroke (greyscale 256×64). The alpha reveal sweeps head→tail in 90 ms, then fades in 80 ms.<br>**Colour:** units #FFFFFF α 0.55; heroes #FFF3D6 HDR 1.3; crits ×1.3 size, HDR 1.8.<br>**Pool:** 24.<br>**Tier:** Busy keeps importance ≥ 3, selected units and crits; Brawl keeps heroes and crits. | New `src/fx/smears.gd` (pooled MeshInstance3D) + `smear.gdshader` (`reveal`, `fade`, `tint`), triggered by the UnitView swing phase. | usually < 8 draws, peak 24 | P0 |
| CMB-21 | **Micro-knockback wobble + victim tremble** | `hit_landed` on a mobile unit | **Direction** d = flat(victim − src).<br>**Amplitude** A = base × clamp(0.6 + amount/(0.08 max_hp), 0.6, 1.6) × (crit 1.6) / mass. Base per weapon: pierce 0.05, slash 0.07, chop 0.08, claw 0.07, blunt 0.11, magic 0.06, siege 0.18 m.<br>**Spring:** an impulse v0 = 1.52 A ω on the body offset (ω 24, ζ 0.32), giving about 2 visible wobbles that settle in ≈ 450 ms; offset length ≤ 0.18 m. Tilt away = offset × 1.2 rad/m about the feet.<br>**Modifiers:** swinging ×0.6; holding ×0.5; flyers ×1.4 plus a vertical bob ×0.5; structures: no wobble, but a siege hit gives an 80 ms shudder of ±0.04 m.<br>**Tremble:** 70 ms of ±0.025 m at 30 Hz, decaying linearly (per-unit RNG), layered on top. Rings and bars never move. | Layer `react`, using the FND-1 spring per axis. | ~1 µs per reacting unit | P0 |
| CMB-22 | **Critical strike punch** (no slow-mo) | `hit_landed` with CRIT | **Attacker:** 80 ms hold; smear ×1.3 at HDR 1.8.<br>**Victim:** 110 ms flash; knockback ×1.6; sparks ×1.5.<br>**Ground shock ring:** r 0.4→1.4 m over 200 ms (`out_quad`), #FFF1D6 α 0.7→0.<br>**Number:** "N!" (CMB-28). **Sound:** crit sweetener.<br>**No** camera shake and **no** time scaling: the punch comes from the hold, the ring and the number pop. | `vfx.gd` + layer `react`; ring = FxSprites `shock-ring`. | +1 sprite | P1 (when crits exist in gameplay) |
| CMB-23 | **Whiff, miss and dodge** | `attack_released(connected = false)` (happens today when the target escapes the range buffer); `attack_missed` (evasion, later) | **Whiff:** the smear plays with no flash or sparks; whoosh sound only.<br>**Miss:**<br>• the victim dodges: 0.12 m sideways (side from the per-unit RNG) and 8° roll, springing back (ω 16, ζ 0.6);<br>• "miss" text #D8D2C8 italic 15 px rises 24 px over 600 ms, shown only if the local player owns the attacker or the victim;<br>• a ranged miss carries on 2.5 m past the target along its last velocity (150 ms visual continuation), then sticks in the ground (CMB-25). | `vfx.gd` + layer `react`. | trivial | P0 whiff / P1 miss |

**CMB-16 pose sketch (pure function, unit-tested):**

```gdscript
static func melee_pose(s: float, dp: float, h: float) -> float:
	if s < dp:
		var u := s / dp
		if u < 0.62:
			return -0.30 * Juice.out_quad(u / 0.62)                       # pull back, settle into the load
		return lerpf(-0.30, 1.0, Juice.in_cubic((u - 0.62) / 0.38))       # snap, accelerating into contact
	if s < dp + h:
		return 1.0                                                        # visual hit-stop (sim unaffected)
	return 1.0 - Juice.out_back((s - dp - h) / maxf(1.0 - dp - h, 0.001), 1.3)   # recover, 6 % dip
```

### 4.4 Ranged attacks and projectiles

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| CMB-24 | **Ranged release tells** (bow, gun, caster, thrower) | ranged wind-up; `attack_released` | **Bow:** draw D = `in_out_sine`(min(u/0.85, 1)), held at full draw for the last 15 %, mapped to lean-back 0.16 rad. Bow bend: scale along the string axis 1→0.9. On release: string snap (bow scale jitter, 3 cycles in 60 ms), body recoil 0.04 m back (spring ω 20, ζ 0.4), a 0.2 m white flick streak for 50 ms, and the twang sound.<br>**Gun:** muzzle flash #FFD27A HDR 3, 0.45 m, 45 ms; 3 smoke puffs #BFB8AC 0.3→0.8 m over 700 ms, rising 0.4 m/s; recoil 0.08 m (ω 20, ζ 0.4).<br>**Caster:** a hand-glow sprite at the launch point grows 0.05→0.3 m, HDR 0→2.0, across the wind-up, in `fx.spell_color` (never team colour). Release flash 70 ms. The bolt is a core sprite at HDR 2.5 plus 6 trail sprites every 0.1 s (life 250 ms). Impact: an ethereal-style burst in the spell colour and a 0.6 m ring.<br>**Thrower:** arm-back pose (pitch −8°) during the wind-up, no flash. | `unit_view.gd` (poses), `vfx.gd` (sprites), and a visual child in `projectile.gd` (bolt and trail). | ~3–8 sprites per shot | P0 bow / P1 others |
| CMB-25 | **Arrows: trail, ground stick, pincushion ★** | in flight; `projectile_ended` | **Flight:** a 0.5 m streak ribbon behind the arrow (#FFFFFF, α 0.3→0 along its length); fletching rolls at 5 rev/s on a child mesh.<br>**Ground** (target died, or a miss): the arrow sticks at its flight pitch, clamped to 25–60°, 30 % embedded. It wobbles about the embed point (amplitude 10°, ω 70 rad/s ≈ 11 Hz, ζ 0.18, ≈ 0.4 s) with 2 dust sprites and a "thunk". It stays 6 s, then sinks over 0.4 s. Ring buffer of 128.<br>**Unit hit ★:** an arrow attaches to the victim's **body** at the hit point (body-local, so it rides the knockback and topples with the corpse).<br>• ≤ 3 per unit (oldest removed); each lives 3 s then shrinks over 200 ms.<br>• Corpses keep theirs until the dissolve stage.<br>**Building hit:** sticks 8 s, ≤ 24 per building. | New `src/fx/stuck_arrows.gd`: one MultiMesh, per-instance owner id + local transform, updated only for on-screen owners. `projectile.gd` adds the streak child. | 1 draw; ≤ 0.1 ms | P0 trail + ground / P1 pincushion |
| CMB-26 | **Thrown weapons: spin-to-land** | projectile `model` = axe/hammer/spear/glaive | **Axes and hammers** tumble about their lateral axis by n = max(1, round(T_flight × 2.5)) full turns, so the head leads at impact: angle = n·2π·k with k = `Projectile.progress()`. Yaw wobble ±6°. On a hit: material sparks, then the weapon ricochets (falls beside the victim with one 0.3 m bounce and fades over 1.2 s). It never sticks in a body.<br>**Spears and javelins:** no spin; they stick like arrows and stay 6 s.<br>**Glaives:** spin about Y at 6 rev/s with a 0.3 m motion-ring trail. | `projectile.gd` visual child; T_flight = distance / speed, taken at launch. | trivial | P1 |
| CMB-27 | **Siege shells: smoke, ground shadow ★, scorch, recoil** | siege `attack_released`; `projectile_ended` | **Launch:** flash #FFC46B HDR 3, 0.6 m, 60 ms; a smoke ring of 8 sprites expanding radially at 1.2 m/s (#A8A196, life 900 ms); attacker recoil 0.25 m (ω 14, ζ 0.35).<br>**Flight:**<br>• the shell tumbles at 1 rev/s, dropping a smoke puff every 45 ms (0.25→0.7 m, life 800 ms, #9C968C α 0.5);<br>• **ground shadow:** a blob under the shell shrinks from 0.9 to 0.5 m radius as its α rises from 0.15 to 0.55 while the shell falls, so the arc reads from a top-down camera;<br>• the incoming whistle starts at T_flight − whistle_len, so its peak lands on the impact.<br>**Impact:**<br>• flash #FFC46B HDR 3, 0.9 m, 70 ms;<br>• 8 clods #6B5238 (up 3–6 m/s, gravity 12, life 700 ms, ground-clamped);<br>• 6 dust sprites 0.6→1.6 m, life 1.1 s, #B3A48C;<br>• shock ring r 0.3→2.0 m in 260 ms, #FFE8C4 α 0.6→0;<br>• pooled impact light #FFB060, energy 3→0 over 140 ms;<br>• scorch 1.8 m (#2B231C α 0.55) for 20 s plus a 4 s fade (CMB-32 marks);<br>• camera trauma +0.12, only within 14 m of the camera focus. Shake = trauma² × (0.25 m, 0.6°), decaying at 1.6/s; combat contributes at most 0.35 total. The camera doc owns the shaker.<br>Building hits throw debris chunks instead of leaving a scorch. | `vfx.gd` + `projectile.gd` + `ground_marks.gd` + `impact_lights.gd`. | ≈ 25 sprites per shot; 1 light | P1 |

### 4.5 Numbers and health bars

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| CMB-28 | **Combat text policy, crit pop, bounty + coin flight ★** | `hit_landed` (crit/heal/miss); `bounty_awarded` | **Policy** (setting "Combat text"):<br>• **Minimal** (default): crits, bounty, heals ≥ 10, mana drained or absorbed, and misses involving the local player.<br>• **Detailed:** also every hit dealt or taken by the local player's *selected* units.<br>• **Off.**<br>Today's `vfx.gd` prints every hit: change it to Minimal.<br>**Merge:** a second number for the same (target, kind) within 250 ms adds into the existing label (value += n, bump to scale 1.12 over 60 ms, life = max(remaining, 0.5 s)).<br>**Style:** Label3D `fixed_size`, `no_depth_test`, `render_priority` 20, bold UI numeric font, 6 px outline #120A04 α 0.9. Heights at 1080p: normal 16 px, heal 18, bounty 22, crit 30. Spawn at the bar top + 10 px, rise 40 px (`out_cubic`), alternate ±8 px sideways, fade over the last 30 %.<br>**Crit "N!" #FF4433:** scale 0→1.45 in 90 ms (`out_back`), 1.0 by 220 ms, hold to 700 ms, gone by 1000 ms.<br>**Detailed colours:** dealt #F2EEE6, taken #FF6A55. **All modes:** heal "+N" #7CFF8A, mana #4FA8FF.<br>**Bounty:** "+N" #FFD34D with a spinning coin glyph (2 rev/s), 1.2 s, fade over the last 35 %. Lumber "+N" #8EDB6A with a leaf glyph, 20 px below.<br>**Coin flight ★** (local player only, kill on screen):<br>• 1 coin for N < 20, 2 for N < 40, 3 for N ≥ 40, as 2D HUD sprites flying from the kill's screen position to the gold counter in 520–680 ms;<br>• path: quadratic Bézier (control point 120 px above the start), t eased `in_quad`, scale 1→0.6, spinning;<br>• arrival bumps the counter (1→1.15→1 over 160 ms) with a coin tick (≤ 6/s);<br>• **the counter value updates immediately; only the bump waits for the coin;**<br>• at most 6 coins in flight. | Split a new `src/fx/combat_text.gd` out of `vfx.gd`. Coin flight lives in `hud.gd` (the counter belongs to the UI/economy doc). | ≤ 24 Label3D; ≤ 6 sprites | P0 policy + crit + bounty / P1 coin flight, Detailed |
| CMB-29 | **Health bars: ramp, damage ghost, flash, heal preview, low-HP hatch** | every frame; `hit_landed`; heals | **Fill ramp:** ≥ 0.66 #33CC4A; 0.33–0.66 lerp to #F2CF2E; below 0.33 lerp to #E8402A.<br>**Ghost:** on damage, the lost segment [hp, hp_before] turns #FFE3A0. It holds for 400 ms after the latest hit, then drains with `damp` at 7/s, at no less than 0.25 bar/s.<br>**Heal:** a #B8FFB0 segment appears at the new value and the fill catches up in 220 ms (`out_quad`).<br>**Flash:** the border goes #FFFFFF for 70 ms on damage (Busy and Brawl: own units, heroes and selected only).<br>**Low HP (< 25 %):** 45° hatch stripes in the fill (6 px period, stripes at ×0.65 value) scrolling at 10 px/s: a colour-blind-safe danger cue. Heroes also double-pump the bar (scale 1→1.06→1→1.04→1 every 0.8 s).<br>**Hero bars:** a 1 px gold border #D8B45A, so they can be found in a crowd.<br>**Reveal while bars are hidden** (no Alt, not always-on): units damaged in the last 2.5 s, selected units and the hovered unit show bars, fading out over 300 ms. Can be turned off in settings. | `health_bars.gd`:<br>• move width and height into the instance basis scale;<br>• `INSTANCE_COLOR` = (ghost, flash, heal target, bar alpha);<br>• `CUSTOM` = (hp, mana, flags: hero/hatch, spare);<br>• per-unit visual state keyed by id, updated only while active.<br>`health_bar.gdshader` draws the segments and the hatch. | still 1 draw; ±0.05 ms CPU | P0 ramp + ghost + flash / P1 hatch, reveal, hero border |

### 4.6 Death and aftermath

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| CMB-30 | **Death beat, directional topple, body-fall sync** | `unit.alive == false` (`dead_time()`), plus the last-hit cache and KILL flag | **0–60 ms "death beat":** the pose freezes in its hit reaction and the flash holds at 1.0 (white).<br>**60–560 ms topple:** the body rotates about its feet *away from the killer* (last hit direction, ±20° yaw variance from the per-unit RNG), 0→90° with `in_quad` (gravity), sliding 0.15 m.<br>**560 ms contact:** a ring of 6 terrain-coloured dust sprites at the hip and the body-fall thud (pitch 1.1 − 0.1 × mass, clamped 0.8–1.1). Bounce back 7° over 80 ms (`out_quad`), then settle over 120 ms.<br>**Overkill** (final blow ≥ 50 % max HP, siege or crit): the body is launched 0.9 m (clamped) along the hit direction with a 0.6 m peak over 380 ms, rolling an extra 120°; landing dust ×1.5.<br>**Clip units:** the `death` clip is remapped so `death_contact` lands at 560 ms (rate clamped 0.8–2.0×; the 2.97 s infantry clip plays at ≈ 1.6×). Dust and sound fire at contact.<br>**No corpse** (`fx.corpse = none`: summons, ethereal): the body scales to 0 in 250 ms (`in_back`) and bursts into 14 motes in the spell colour rising 1.2 m over 800 ms, with an implosion ring of 0.6 m.<br>**Separate weapon node:** detaches at 300 ms, bounces once and settles at about 20°.<br>**Ring and bar** disappear on the death frame. | Replaces `UnitView._animate_death()`. `vfx.gd` keeps the last-hit direction per unit id. Heroes: heroes doc. Structures: world/economy doc. | trivial | P0 |
| CMB-31 | **Corpse decay stages + team-colour ebb ★** | `dead_time()` against D = `decay_ticks()` × DT (8 s by default; stages scale with D) | Seconds below are for D = 8.<br>**Fresh (0.7–3.6 s):** team-colour *ebb*. From 0.7 s, `team_sat` falls 1→0.2 over 1.4 s, sweeping from feet to head (front = top × `in_out_sine`(k), 0.15 m soft edge). The flag is lowered, so a corpse never reads as a live unit. Value ×0.85.<br>**Dissolve (3.6–5.6 s):** a noise dissolve 0→1 with a dusty edge #5A4A3A (0.05 m) reveals a generic **remains** prop (3 size classes: bones and dented gear, desaturated) at the body's resting transform. 4 dust motes drift up.<br>**Remains (5.6–6.5 s).**<br>**Sink (6.5–8.0 s):** the remains sink 0.25 m and dither out; stuck arrows go with them. Then the stain hand-off (CMB-32).<br>**No remains asset:** skip the dissolve and sink the body (today's behaviour). | `unit.gdshader` instance uniforms `team_sat`, `sat_front`, `dissolve` (`discard` in the opaque pass, so there is no sorting cost). Remains: `assets/models/fx/remains_{s,m,l}.glb`. | shader cost only on corpses | P0 ebb + sink / P1 dissolve + remains |
| CMB-32 | **Battlefield memory ★** (ground stains and scorches) | corpse removal; siege impact; shared with building-death scorch | A terrain-aligned quad at the corpse: a trampled-grass and darker-soil stain (painted atlas, 4 variants, random rotation). Radius 0.6–1.1 m by size class. It multiply-darkens by at most 22 % (#3E3326 α 0.22) and adds no hue.<br>**Life:** 90 s, fading over the last 20 s. **Cap:** 96; the oldest fades first.<br>Overlaps accumulate, so a contested choke visibly scars over a match.<br>It samples `fog_tex` (hidden in unexplored areas, dimmed in fog) and renders below rings and markers. | New `src/fx/ground_marks.gd`: a MultiMesh of quads tilted to the terrain normal (as `SelectionCircles` does), with spawn time packed in the instance basis (as in FND-2), plus `ground_mark.gdshader`. | 1 draw | P2 |

### 4.7 Personality and state

| id | feature | trigger | exact spec | Godot implementation | perf cost | prio |
|---|---|---|---|---|---|---|
| CMB-33 | **Wounded gait and panic run** | hp/max < 0.30 (exit above 0.40); retreating = moving, damaged in the last 2 s, and moving away from the last attacker (dot > 0.3) | **Wounded:** stride asymmetry (one half-cycle 15 % shorter), roll ±4° at stride frequency, hunch pitch +5°. Idle breathing runs ×1.8 amplitude at 1.6 Hz (panting). Fades in over 400 ms.<br>**Panic:** lean +10°, and an over-the-shoulder glance at the attacker every 0.9 s (300 ms, via the CMB-06 head).<br>**Workers:** an extra +6° hunch when panicking; hit while working → a 250 ms flinch (10 % crouch).<br>**Leashing creeps** walking home: head down, pitch +8°. | Layers `wounded` and `panic`, reading the Vfx last-hit cache. | trivial | P2 |
| CMB-34 | **Hero swagger and heavy footfalls** | `unit.is_hero` | **Breathing:** period 3.6 s, amplitude 3.5 %.<br>**Weight shift** every 4.5–7 s: roll 4°, held 1.2 s.<br>**Chest out:** idle > 8 s with no enemy within 20 m → sy 1.03 + pitch −4° for 600 ms, every 10–16 s; uses a `flourish` clip when the GLB has one.<br>**Walk:** dust ×1.6 per plant, stride 1.1×. The local *selected* hero thumps softly on every other step at −18 dB.<br>**Ground glow ring** (owned by the heroes doc): pulses α 0.9↔1.0 at 0.5 Hz.<br>**Kill-confirm:** the big variant (CMB-35). | Layer `idle` with hero parameters. | trivial | P1 |
| CMB-35 | **Kill-confirm** | `hit_landed` with KILL, killer on screen | At the killer's backswing end (or 250 ms after a ranged kill): a 300 ms chin-up (pitch −5°, sy 1.04, settling with `out_back`) and a 25 % team-rim brighten for 200 ms (`rim_boost`), showing *who* got the kill.<br>**Heroes** with no other target in acquire range raise the weapon overhead (pose 1.2, held 600 ms). 10 % chance of a hero warcry (audio doc; 20 s cooldown).<br>**Tier:** Busy keeps heroes only; Brawl turns it off. | Layer `ack` + `rim_boost`. | trivial | P2 |

### 4.8 Reference tables used by the rows

**Material × weapon hit matrix (one hit, Calm tier, normal effectiveness).** Counts are then scaled per CMB-18 and CMB-19.

| material (`fx.material`) | additive layer (blooms) | alpha layer | impact sound family |
|---|---|---|---|
| metal | 7 spark streaks #FFF3C4→#FF9B30, HDR 2.5, 4–7 m/s, gravity 9.8, drag 1.5, life 180–260 ms; 1 star flare #FFF6EC 0.5 m, 60 ms | n/a | `hit_metal` |
| wood | n/a | 5 splinters #8B5A2B / #B07A45, 0.08 m, spin 8–14 rad/s, 2–4 m/s, gravity 9.8, life 400 ms, ground-clamped; 1 sawdust puff #D9B77E 0.3→0.6 m, 350 ms | `hit_wood` |
| flesh | 1 impact star #FFF6EC, HDR 1.6, 0.4 m, 70 ms | 4 droplets #C8323C / #E2575E, 0.10 m, 2–3.5 m/s, gravity 12, life 300 ms, ground-clamped (Gore Off: dust #D9CBB0) | `hit_flesh` |
| stone | 1 flare #FFF0D0, HDR 1.4, 50 ms | 5 chips #8E8579 / #6E675E, 0.07 m, 2–4 m/s, gravity 12, life 450 ms; dust puff #B9AE9C 0.4→0.9 m, 500 ms | `hit_stone` |
| bone | 1 star #F4EEDC, HDR 1.3, 50 ms | 4 bone chips #E8DDC0, 0.06 m, tumbling, life 400 ms; dust #CFC2A0 | `hit_bone` |
| ethereal | 8 motes #A6F0FF, HDR 2.2, 0.08 m, 1.5 m/s rising (gravity −2), life 500 ms; ring #6FD8FF r 0.2→0.6 m, 200 ms | n/a | `hit_ethereal` |

| weapon (`fx.weapon`) | count × | cone and direction | extra layer |
|---|---|---|---|
| slash | 1.0 | 50°, along the swing tangent | smear (CMB-20) |
| chop | 1.3 | 60°; chips ×1.3 size | smear |
| blunt | 1.1 | 80°, biased upward | dust ground ring r 0.2→0.8 m over 150 ms, α 0.4; knockback base 0.11 |
| pierce | 0.6 | 25°, along the shot/thrust (arrows exit the far side) | none |
| claw | 1.0 | 3 parallel streaks + material layer | 3-line smear |
| magic | 0.8 | radial | the material layer becomes a burst in `fx.spell_color` |
| siege | n/a | n/a | CMB-27 |

**Combat sound layering** (buses and priorities follow `audio-direction.md` §3.5; positional, culled at 50 m, honours fog):

| layer | fires at | rule |
|---|---|---|
| whoosh | swing snap start (u = 0.62), including whiffs | family by `fx.weapon`; Brawl: heroes only |
| impact | `hit_landed` | material × weapon family; CMB-19 swaps to "tink"/"thud" or adds "crack" |
| crit sweetener | `hit_landed` with CRIT | priority 80 |
| pain vocal | `hit_landed` (victim) | 20 % chance, 1.2 s cooldown per unit type, never on structures |
| death vocal / body fall | death / topple contact at 560 ms | body-fall pitch set by mass (CMB-30) |
| launch | ranged `attack_released` | twang / throw vocal / boom |
| incoming whistle | T_flight − whistle_len | siege only, flights ≥ 0.6 s |
| stick thunk | `projectile_ended` on the ground | ≤ 4/s |

---

## 5. Our own twists (things WC3 did not have)

Each twist reports a real game fact, so it adds clarity rather than noise.

1. **Order ripple (CMB-10).** WC3 confirms with one voice and one ground blip. We send a visible wave of ring pulses and nods through the whole selection, starting from the unit nearest the click. You *see* that all 12 units heard you, and late path starts no longer look like ignored orders.
2. **Stance tells (CMB-07).** In WC3 a unit on Hold looks exactly like an idle one. Ours crouch behind their shields, attack-movers raise their weapons, patrols scan side to side, and engaged units never relax between swings. The order state reads straight off the battlefield.
3. **Fourth-wall glance (CMB-15).** Annoyed units physically turn to the camera and shake their heads while they complain. This gives WC3's beloved "pissed" lines a body.
4. **Effectiveness tell (CMB-19).** Pierce on heavy armour *dinks*; siege on a fortified building *cracks*. Players learn the attack/armour chart by feel, with no tooltip.
5. **Painted smears (CMB-20).** Swing trails use a hand-painted dry-brush stroke, not a neon ribbon, so they belong to the hand-painted diorama style.
6. **Pincushion arrows (CMB-25).** Arrows stay stuck in their victims (≤ 3, for 3 s) and in the ground. You can read *who is being shot* in a blob, and the arrows ride the knockback and fall with the corpse.
7. **Team-colour ebb (CMB-31).** On death the team colour drains from feet to head like a flag being lowered. Fresh corpses can never be mistaken for living units, and every death gets a quiet emotional beat.
8. **Battlefield memory (CMB-32).** Trampled, darkened ground persists for 90 s, so a choke that was fought over all game looks scarred. It is environmental storytelling that never adds colour noise.
9. **Creep notice (CMB-06).** Creeps lift their heads and turn toward you at 1.5× their aggro range, so you can feel the pull distance before you trip it.
10. **Guard ring (CMB-05).** A parked squad turns outward and watches its perimeter instead of standing in a parade line.
11. **Siege ground shadow and timed whistle (CMB-27).** A shrinking shadow shows where a shell is in depth from the top-down camera, and the whistle crescendos into the impact.
12. **Voice-driven portrait (CMB-14).** The portrait nods on the syllables of the actual audio envelope, which works for every AI-generated line with no hand animation.
13. **Bounty coin flight (CMB-28).** Coins arc from the kill into the treasury and bump the counter. The number itself updates instantly, so the coins are celebration, never delay.
14. **Kill-confirm (CMB-35).** The killer lifts its chin for 300 ms, so even in a blob you can tell who landed the blow.
15. **Eyes-first order glance (CMB-06).** Heads turn toward the marker in the same frame as the click, hiding the 33 ms tick plus any path-budget latency. RTS controls feel tighter without touching the sim.

---

## 6. Anti-patterns (rejected in review)

1. **Real hit-stop or slow motion.** No `Engine.time_scale`, no sim pause and no delayed damage. Hit-stop is a hold on the attacker's visual pose only.
2. **Frame-rate-dependent smoothing.** No `lerp(a, b, 0.1)` per frame, no Euler-integrated stiff springs, no counting frames. Use `damp`, the closed-form spring and timestamps.
3. **Free-running attack clips.** A blade that visibly lands 200 ms before or after the HP drops. Attack and death clips are always seeked from sim phase (CMB-16, CMB-30).
4. **Damage confetti.** A number on every hit is MMO noise. The default is Minimal (CMB-28).
5. **Screen shake for routine combat.** Only siege impacts near the camera focus (capped) and the hero events owned by other docs may shake.
6. **Fake blocks or parries.** A shield "blocking" a hit that still deals damage lies to the player. Feedback must match the outcome.
7. **Resource counters that lag behind the sim** to sync with a coin animation. The display must never lie.
8. **Synchronised idling.** A whole army breathing or fidgeting in lockstep (the "chorus line"). Use per-unit phases and the fidget token bucket.
9. **Generic AI-slop juice.** The same pop-scale bounce on everything, one easing curve for all motion, rainbow or glitter particles, everything glowing. Every row here has its own curve, tied to a physical idea such as load, snap, recoil or settle.
10. **Bloom on units.** Team colour or flash emission above 1.0. Only VFX bloom (unit flash emission ≤ 0.6).
11. **A node per effect per unit.** 300 `GPUParticles3D`, an `OmniLight3D` per projectile, or a mesh and material allocated per click (today's `CommandInput._marker` does this). Pool everything and use FxSprites.
12. **Tweens fighting over `body`.** Several `create_tween()` calls on `body.scale` and `rotation`. One composer, one write.
13. **Writing visual offsets to the sim-owned `Unit` transform.** That breaks interpolation and picking. Offsets go on `body` only.
14. **Effects that hide information.** Big puffs over health bars, red gore washing out a red team colour, smears covering team colour for longer than about 90 ms. Respect the render order and caps in §2.
15. **Fog and invisibility leaks.** Sparks, dust, sounds or a creep "notice" revealing a unit the local player cannot see.
16. **Popping corpses.** A body that blinks out of existence. Always ebb, dissolve or sink.
17. **Effects that outlive their information.** Sparks over 400 ms, numbers over 1.3 s, stains with colour.
18. **`Decal` nodes.** They are unsupported on Compatibility. Use terrain-aligned quads (ground marks, rings).
19. **Copying WC3's specific VFX.** No reproduction of WC3's own missile, blood or death-effect art or timing as a signature. Generic conventions (a red crit number with "!", a green move blip, corpses decaying to bones) are fine. Our shapes, textures and curves are original.

---

## 7. Budgets, governor and verification

**Budget (300 units, about 150 on screen, Brawl tier, mid-range GPU at 60 fps):**

| resource | budget |
|---|---|
| GDScript CPU for all combat juice (composer, router, markers, text) | ≤ 1.5 ms/frame |
| Draw calls added by this domain | ≤ 20 (2 FxSprites, 1 stuck arrows, 1 ground marks, ≤ 8 smears, ≤ 8 markers/flags/lines) |
| Live sprites | ≤ 2560 (1536 alpha + 1024 additive), ≤ 400 of them large (> 0.8 m) |
| Label3D combat text | ≤ 24 |
| Lights | 4 pooled impact lights, no shadows |
| GPUParticles3D nodes | 0 in this domain. FxSprites covers it because it handles hundreds of tiny bursts per second without per-node cost or `restart()` truncation, and it is identical on Compatibility. A pooled GPUParticles3D set is reserved for spell-scale effects in the heroes/VFX doc. |

**Verification (add with the implementation; no test may be skipped):**

1. `tests/unit/test_juice_determinism.gd`: run the `battle_setup` scenario for 60 sim-seconds with visuals and juice on, and again with `World.visuals = false`. Hash (id, pos, hp) every second; the hashes must be identical.
2. `tests/unit/test_juice_framerate.gd`:
   - Step `Juice.spring` and `damp` with dt sequences for 30, 60, 144 and 240 Hz and with random jittered dt. End states at 0.5 s must match within 1e-4.
   - FxSprites `age = now − t0`, given the same `Vfx.now`, must be identical.
3. `tests/unit/test_swing_pose.gd`: `melee_pose(dp) == 1.0`; `melee_pose(s) < 1.0` for all s < dp; monotonic snap after u = 0.62; the recovery ends at 0 ± 1e-3.
4. `tests/playtest/brawl_juice.gd`:
   - Run 150 vs 150 (melee, archers, one siege).
   - Save screenshots in the Calm, Busy and Brawl tiers.
   - Log the frame-time histogram, live sprite counts, Label3D counts and the lights in use.
   - Assert every cap is respected.
   - Run one capture on Compatibility (`opengl3`).
5. Fog-leak test: an enemy in fog fighting a creep produces zero sprites, labels and sounds (Vfx counters).

**Files touched (checklist):**

- New in `src/fx/`: `juice.gd`, `fx_sprites.gd` + `fx_sprite.gdshader`, `combat_text.gd`, `order_markers.gd`, `waypoint_lines.gd`, `rally_flags.gd`, `smears.gd` + `smear.gdshader`, `stuck_arrows.gd`, `ground_marks.gd` + `ground_mark.gdshader`, `impact_lights.gd`.
- New `src/entities/unit.gdshader` and `tools/bake_clip_markers.gd`.
- Changed:
  - `unit_view.gd`: composer, swing and death remap.
  - `vfx.gd`: router, clocks and governor.
  - `health_bars.gd` + `health_bar.gdshader`.
  - `selection_circles.gd` + `ring.gdshader`.
  - `projectile.gd`: visual children and `progress()`.
  - `command_input.gd`: uses `OrderMarkers` and emits the glance and ripple.
  - `unit.gd`: `prev_facing`, readers, `attack_released`.
  - `combat.gd`: `hit_landed`, `projectile_ended`.
  - `events.gd`, `audio.gd` (`voice_started`), `hud.gd` (portrait driver, coin flight), `doodads.gd` (`shake`), `map_data.gd` (`tex_at`), `defs.gd` (`fx` defaults).
  - `data/units.json`: `fx` blocks.
  - `docs/architecture.md` §5 and §11, in the same commit.

**Cross-doc contracts:**

- **Camera doc:** owns the trauma shaker; this doc only *requests* trauma (CMB-27).
- **Audio doc:** owns buses, caps and the mixer; this doc defines *when* each layer fires.
- **Heroes/VFX doc:** owns hero glow, level-up, revive, hero death and spell particles.
- **World and economy docs:** own building damage fire, collapse, construction, creep sleep, mine and tree feedback, and income popups. They reuse FxSprites, ground marks and the governor from this doc.
- **UI doc:** owns the portrait viewport, fonts, the HUD counter art and marker sounds.
