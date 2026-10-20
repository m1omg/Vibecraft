export const meta = {
  name: 'engine-skeleton',
  description: 'Build the Vibecraft Godot 4.7 engine skeleton (core sim, terrain, pathing, units, camera, selection, combat, HUD stub, tests), then review and fix',
  phases: [
    { title: 'Core', detail: 'project, autoloads, grid/map/terrain/pathing, units+movement, camera, selection' },
    { title: 'Combat', detail: 'orders, attacks, projectiles, death, HUD stub, playtest' },
    { title: 'Review', detail: '2 reviewers with different lenses' },
    { title: 'Fix', detail: 'apply verified findings, re-run tests' },
  ],
}

const REPO = '/home/user/Vibecraft'
const ENV = `
ENVIRONMENT:
- Repo: ${REPO} (git repo, branch claude/clever-heisenberg-i8649y). Do NOT commit or push; the lead will commit.
- Godot 4.7.2-stable binary: /usr/local/bin/godot . Use GDScript 2.0 (Godot 4 syntax only: @export, @onready, typed arrays, Callable, signal.emit(), etc.).
- Headless check: cd ${REPO} && godot --headless --path . --import  (builds .godot cache; then) godot --headless --path . -s tests/run_tests.gd
- Rendering for screenshots (software Vulkan): VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a -s "-screen 0 1600x900x24" godot --path . --rendering-driver vulkan -s <script>  (slow but works; keep scenes small, use --resolution 1280x720). OpenGL fallback: --rendering-driver opengl3.
- Python 3.13 with Pillow available; Blender bpy at /opt/bpyenv/v313/bin/python (not needed now).
- READ ${REPO}/docs/architecture.md FIRST. It is the contract. Follow its layout, names, units of measure and rules (fixed 30 Hz tick + physics interpolation, data-driven defs, placeholder visuals, headless tests). If you must deviate, update docs/architecture.md accordingly and explain why.
- The user's hard requirement: the game must be independent of display refresh rate. Gameplay only in the fixed tick; visual-only code in _process with delta.
- Game content (faction/unit names) is NOT decided yet: use neutral placeholder defs in data/units.json like "dummy_worker", "dummy_soldier", "dummy_archer", "dummy_hall", "dummy_barracks", "gold_mine". Never use Warcraft names.
- Code quality: static typing where practical, small focused functions, comments only where non-obvious. No warnings-as-errors failures; fix parse errors and runtime errors you see in output (grep for "SCRIPT ERROR", "Parse Error", "ERROR:").
- Performance target: 200+ units at 30 Hz tick in GDScript. Avoid per-frame allocations in hot loops; use SpatialHash; budget A* queries per tick.
`

phase('Core')
const core = await agent(`${ENV}
TASK (part 1 of 2): Build the engine CORE from scratch (the repo only has docs/ and .gitignore).
Deliver:
1. project.godot: app name "Vibecraft", main scene src/main.tscn, Forward+ renderer (rendering/renderer/rendering_method="forward_plus", with gl_compatibility fallback allowed), physics ticks 30, physics interpolation on, window 1600x900 (resizable, stretch mode canvas_items/expand), MSAA 2x 3D, autoloads (Defs, Events, Settings, Audio), input map actions (camera pan WASD? NO - WC3 uses arrows; use arrow keys for pan, mouse wheel zoom, middle-drag pan; selection: left click; command: right click; control groups ctrl+0..9; shift modifier; Esc cancel; F10 menu; space = jump to last alert; tab = subgroup cycle; grid hotkeys Q W E R / A S D F / Z X C V for the command card).
2. src/autoload: defs.gd (loads data/*.json, validates required fields, provides Defs.unit(id), Defs.ability(id), etc.), events.gd (signals from the architecture doc), settings.gd (user settings: edge pan speed, etc.), audio.gd (stub API: play_ui(id), play_3d(id, pos), play_voice(unit, category) — silently no-op when assets missing).
3. src/world: grid.gd, map_data.gd (JSON loader + programmatic generator for a test map: 96x96 tiles with 2-3 cliff levels, ramps, a lake, tree clusters, 2 start locations with gold mines, 4 creep camp spots), terrain_builder.gd + terrain.gdshader (chunked mesh, cliffs with walls, ramps, splat blending of up to 8 layers — for now procedural colour/noise placeholders per layer since textures aren't made yet; design the shader to accept a Texture2DArray later; triplanar rock on cliff walls; fog texture uniform hook), pathing.gd (AStarGrid2D 0.5 m cells, footprints, find_path with string-pulling, per-tick query budget), spatial_hash.gd, doodads.gd (trees as MultiMesh with placeholder procedural tree mesh - cone+cylinder, per-tree lumber, removal on depletion updates pathing), world.gd + world.tscn (system order per architecture doc, spawn helpers, issue(command)), day_night.gd (sim-time based cycle; directional light colour/angle lerp, visual only).
4. src/entities: unit.gd (fields from architecture doc; order queue; MOVE/STOP/HOLD/PATROL implemented with path following + separation steering; sample terrain height), order.gd, unit_view.gd (placeholder procedural model per unit def "shape" hint: capsule humanoid with head sphere + team-colour band; buildings as stylised box+roof; procedural animation: idle breathe, walk bob, lean; physics interpolation friendly).
5. src/input: rts_camera.gd (WC3-like: pitch ~-56 deg, FOV ~45, zoom range, edge pan, arrow pan, middle drag, clamp to map; in _process with delta), selection.gd (click, drag box with screen-space rect drawn via a Control overlay, shift add/remove, ctrl+click/double-click select all same type on screen, control groups with ctrl+N / N / double-tap centring), command_input.gd (right-click smart move; shift queue; emits commands via world.issue()).
6. src/fx: selection circles (one MultiMesh or decal-like flat ring meshes under units, team-coloured; green for own, red enemy, yellow neutral) and health bars (billboard quads via MultiMesh or a single CanvasLayer drawing — must be cheap for 200 units).
7. src/main.tscn + main.gd: boots World with the generated test map, spawns 2 players (player 0 human, player 1 enemy), a hall + 5 workers + a few soldiers for each, camera at player start.
8. tests/run_tests.gd test runner + tests/unit/test_grid.gd, test_pathing.gd (path around obstacle, unreachable goal snapping, footprint blocking), test_spatial_hash.gd, test_movement.gd (a unit ordered to move arrives within N ticks; refresh-independence: simulate the same command with the sim stepped manually and check same result regardless of how many render frames occur — i.e., sim step is decoupled).
9. tests/playtest/screenshot_overview.gd: boots main scene under a display, waits a few frames, saves screenshots to tests/output/ (gitignored) from the default camera, and from a zoomed-out angle.
Run the headless import + test runner until all tests pass with no script errors. Then take the screenshots with xvfb+lavapipe and LOOK at them (use the Read tool on the PNGs) to confirm the terrain, cliffs, trees, units, selection circles render sensibly; iterate on obvious visual problems (e.g., camera too close/far, terrain inside-out, black materials).
Add tests/output/ to .gitignore.
Final reply: list of files created, how to run, test results summary, known gaps, and the screenshot paths.`, { label: 'build:core', phase: 'Core' })

phase('Combat')
const combat = await agent(`${ENV}
TASK (part 2 of 2): The core engine skeleton has been built by a previous agent (summary below). Read docs/architecture.md and the existing code under src/ first.
Previous agent summary:
${core}

Implement on top of it:
1. Orders: ATTACK (target), ATTACK_MOVE (engage enemies within acquisition range along the way, resume), SMART right-click resolution (enemy -> attack, ally/ground -> move, own building w/ rally -> rally, resource -> gather stub hook), auto-acquire for idle/hold units, HOLD (attack in range, don't chase), unit chasing with path re-requests (throttled), leash rules.
2. src/systems/combat.gd: damage resolution with attack_type x armor_type table + armor formula from architecture doc (put the table in data/factions.json "combat" section with original type names: e.g., attack: "blade", "pierce", "siege", "arcane", "hero", "chaos"; armor: "light", "medium", "heavy", "fortified", "hero", "unarmored"), damage range rolls with a seeded RNG owned by World (determinism), attack cooldown + damage point (backswing), melee vs ranged; projectiles (src/entities/projectile.gd: travel in the fixed tick with arc, homing to target, hit -> damage; visual interpolated). Death: unit_died event, death animation (procedural topple + sink), removal after decay; corpse cleanup; footprint freed for buildings.
3. Floating combat text / hit flash in src/fx/vfx.gd (visual-only, _process).
4. src/ui/hud.tscn + hud.gd: STUB HUD following the layout in the architecture doc (top bar resource counters bound to PlayerState; bottom console with placeholder panels: minimap area, portrait area, selected-unit name/hp/mana/damage/armor text, multi-selection icon grid (coloured squares with unit initials for now), 4x3 command card with buttons Move/Stop/Hold/Attack/Patrol showing hotkeys; clicking a button or pressing hotkey enters targeting mode where needed). Make the HUD a separate CanvasLayer; clicks on HUD must not pass through to the world selection.
5. data/units.json: give dummy units attacks/armor (worker weak melee, soldier melee, archer ranged w/ projectile, hall/barracks fortified, a creep "dummy_creep" neutral hostile).
6. tests/unit/test_combat.gd (type table multipliers, armor formula positive/negative, damage point timing, determinism with seed), test_orders.gd (attack-move engages enemy then resumes; hold doesn't chase; smart command resolution).
7. tests/playtest/battle.gd: scripted battle - 8 soldiers + 4 archers vs 10 creeps; advance the sim; assert one side wins within 90 sim seconds; save 3 screenshots during the fight (tests/output/battle_*.png) and LOOK at them.
Run all tests until green, no script errors. Final reply: files changed/created, test results, screenshots paths, known gaps.`, { label: 'build:combat', phase: 'Combat' })

phase('Review')
const FIND = {
  type: 'object',
  properties: { findings: { type: 'array', items: { type: 'object', properties: {
    file: { type: 'string' }, line: { type: 'number' }, severity: { type: 'string', enum: ['critical','major','minor'] },
    problem: { type: 'string' }, fix: { type: 'string' } }, required: ['file','severity','problem','fix'] } } },
  required: ['findings'],
}
const LENSES = [
  { key: 'correctness', lens: 'CORRECTNESS: find real bugs - GDScript runtime errors, wrong Godot 4.7 API usage, null access, off-by-one in grid math, pathing errors (units stuck, walking through cliffs/buildings), order state machine bugs, combat formula mistakes, input handling bugs (HUD click-through, selection box math with camera), memory/node leaks on death. Run the tests and the playtests yourself and read the output.' },
  { key: 'architecture', lens: 'REFRESH-RATE INDEPENDENCE + ARCHITECTURE + PERFORMANCE: verify all gameplay is in the fixed tick (search for gameplay state changes in _process/_input), physics interpolation correctness (teleports reset), camera smoothness uses delta, conformance to docs/architecture.md, and performance hot spots for 200+ units (allocations per tick, O(n^2) loops, unbudgeted A*). Write a quick perf test spawning 250 units moving/fighting and measure average tick time (Time.get_ticks_usec) headless; report numbers.' },
]
const reviews = await parallel(LENSES.map(l => () => agent(`${ENV}\nYou are a strict code REVIEWER. Do NOT modify source files (you may create temporary test scripts under tests/output/ which is gitignored). Review the code under ${REPO}/src, ${REPO}/tests and ${REPO}/data with this lens:\n${l.lens}\nReport only verified findings (you traced the code path or reproduced it).`, { label: `review:${l.key}`, phase: 'Review', schema: FIND })))
const findings = reviews.filter(Boolean).flatMap(r => r.findings)
log(`${findings.length} findings from review`)

phase('Fix')
const fixed = await agent(`${ENV}\nYou are the FIXER. Apply fixes for these verified review findings (skip any you can prove is wrong, and say why). Then re-run the import, unit tests and playtests until green, and look at the playtest screenshots.\nFINDINGS:\n${JSON.stringify(findings, null, 1)}\n\nFinal reply: per finding fixed/skipped with reason, final test output summary, perf numbers if measured.`, { label: 'fix', phase: 'Fix' })

return { core, combat, findings, fixed }
