# Vibecraft data schema

Every gameplay number lives in `data/`. The `Defs` autoload (`src/autoload/defs.gd`) loads,
fills defaults, cross-validates and serves it; code never hardcodes a stat. This file documents
every field. When you add a field, document it here in the same commit; when you add a check,
add it to `Defs._validate_*` and a test in `tests/unit/test_data.gd`.

Source of truth when numbers disagree: `docs/design/slice-content.json` > `gdd.md` >
`rules.md` > faction docs / `neutrals.md` > `slice-plan.md`. Data ids are lower snake case
and prefixed by owner: `kingdom_*`, `clans_*`, `creep_*`, `critter_*`, `neutral_*`, `item_*`,
`buff_*`, `cmd_*`, `camp_*`. Tests-only ids are `dummy_*` (see `test_defs.json`).

## 0. Conventions

| Thing | Unit |
|---|---|
| distances, ranges, radii, sight | metres (1 Godot unit). Ranges are edge to edge (`Unit.edge_distance`) |
| `footprint` | pathing cells of 0.5 m, `[w, h]` (hall 16x16 = 8 m, production 12x12, supply 8x8, tower 4x4) |
| times, cooldowns, durations | seconds of sim time (converted to 30 Hz ticks by the systems) |
| speeds | m/s; `turn_rate` rad/s |
| percentages | `*_pct` fields are whole percent (`30` = +30 %); `*_factor` fields are multipliers |
| costs | `{"gold", "lumber", "food", "time"}` (missing keys = 0) |
| facing | degrees in map files, radians on `Unit.facing` |
| text | `name` is the display name (English); UI strings that are not entity names are keys into `data/strings/en.json` (`Defs.text(key)`) |

- Keys starting with `_` (e.g. `_doc`) are comments and are skipped by the loader.
- A file may carry a top-level `"rules"` block. Defs deep-merges all of them into `Defs.rules`;
  read with `Defs.rule("economy.gold_per_trip", fallback)`. A leaf defined in two files is a
  validation error. Rule owners: `factions.json` (match, economy, regen, daynight, vision,
  minimap, controls, alerts, ai), `heroes.json` (heroes, xp), `buffs.json` (status),
  `items.json` (items), `shops.json` (neutral), `creep_camps.json` (creeps).
- Validation errors are collected in `Defs.errors` and pushed as engine errors at load (the
  test runner fails on any). `tests/unit/test_data.gd` asserts `Defs.errors` is empty and that
  slice counts match `slice-content.json`.
- Unknown ids in accessors return `{}` and warn once (`Defs.unit("nope")`).

## 1. Loading contract (Defs)

| Table | From | Accessor |
|---|---|---|
| `units` | `units.json` + `buildings.json` + one derived def per hero (+ `test_defs.json` units) | `Defs.unit(id)`, `has_unit`, `unit_ids` |
| `buildings` | the structure subset (`kind` building/resource) | `Defs.building(id)` |
| `heroes` | `heroes.json → heroes` (raw hero data) | `Defs.hero(id)`, `hero_stats(id, level, bonus)` |
| `abilities` | `abilities.json` | `Defs.ability(id)`, `ability_rank(id, rank)`, `ability_levels(id)` |
| `buffs`, `ground_effects` | `buffs.json` | `Defs.buff(id)`, `Defs.ground_effect(id)` |
| `items` | `items.json → items` | `Defs.item(id)` |
| `upgrades` | `upgrades.json` | `Defs.upgrade(id)`, `upgrade_level(id, level)`, `researched_at(id)` |
| `shops`, `services` | `shops.json` | `Defs.shop(building_id)`, `Defs.service(id)` |
| `camps` | `creep_camps.json → camps` | `Defs.camp(id)` |
| `factions`, `combat`, `upkeep`, `team_colours` | `factions.json` | `Defs.faction(id)`, `Defs.combat`, `Defs.upkeep`, `Defs.team_colours`, `combat_default(key, fb)` |
| `doodads` | `doodads.json` | `Defs.doodad(id)` |
| `rules` | every file's `rules` block | `Defs.rule(path, fb)` |
| `strings` | `strings/en.json` | `Defs.text(key)` (returns the key when missing) |
| `scenarios` | `scenarios.json → scenarios` (scripted match set-ups, §15) | `Defs.scenario(id)` |

Derived helpers: `trained_at(unit_id)` (buildings whose card trains it), `xp_for_level`,
`level_for_xp`, `prd_c(p)` (pseudo-random-distribution constant, rules §2.3), `effect_ids()`
(every ability/item `effect`; `EffectRegistry` must resolve each), `target_radius(def)`,
`max_target_radius`, `max_unit_radius`.

`Defs.load_test_defs()` merges `data/test_defs.json` into the tables (the test runner calls it
first; the `sandbox` scenario of `main.gd` too). Real data never references a test id, and a
test id colliding with a real id is an error.

## 2. Entity defs: `units.json`, `buildings.json` (and derived hero defs)

Every object with an id in the sim (`Unit`) has one def. `units.json` holds mobile units
(trained units, transforms, summons, creeps, critters, the ground-item entity);
`buildings.json` holds structures and neutral buildings. An id may appear in only one file.

### 2.1 Common fields

| Field | Type | Req | Meaning / default |
|---|---|---|---|
| `name` | str | yes | display name |
| `kind` | str | yes | `unit` (mobile), `building`, `resource` (gold seam), `item` (ground item entity) |
| `hp` | int | yes | max HP (> 0) |
| `radius` | float | yes | body radius (m, > 0); structures: collision/selection radius |
| `faction` | str | | `kingdom`, `clans`, `creep`, `neutral`, `critter` |
| `class` | str | | timing class, key into `combat.class_timings` (turn rate, damage point, backswing): `worker, melee, ranged, caster, heavy, siege, flyer, hero_melee, hero_ranged, tower, critter` |
| `level` | int | | XP / bounty level. Default: `cost.food` for units, 0 for structures |
| `flags` | [str] | | see 2.4 |
| `armor` | int | | armour value (default 0) |
| `armor_type` | str | | key of `combat.armor_types` (default `unarmored`) |
| `speed` | float | units | m/s; must be > 0 for `kind: unit` unless flag `immobile` |
| `turn_rate` | float | | rad/s; default from `class_timings[class]`, else `combat.defaults.turn_rate` |
| `sight`, `sight_night` | float | | day/night sight (m). Night default = min(sight, `rules.vision.<unit/worker/structure>[1]`) |
| `hp_regen`, `mana_regen` | float | | per s. Defaults: organic units `rules.regen.organic_hp`, else 0; casters `rules.regen.caster_mana` |
| `mana`, `mana_start` | int | | max mana; start mana default min(mana, `rules.regen.start_mana`) |
| `cost` | {gold, lumber, food, time} | | train/build cost; `time` in s; `food` = food used |
| `requires` | [id] | | buildings (or upgrades) the owner must have to train/build it (Tech.requirements_met) |
| `abilities` | [ability id] | | card abilities and passives (commands `cmd_*` included for the card) |
| `attack` | dict | | weapon, see 2.2; `{}` = no weapon |
| `upgrade_damage` | int | | flat damage added per level of a damage research |
| `hotkey` | str | | letter on the producer's card (trains / build menus); validated for collisions |
| `leash` | float | | max distance from guard point when auto-fighting (default `combat.defaults.leash` 14; creeps 18.75) |
| `decay` | float | | corpse lifetime override (s) |
| `model` | str | | `assets/models/<model>.glb` (e.g. `units/kingdom_hodman`, `buildings/kingdom_moot_hall`); `""` or missing file = procedural placeholder |
| `model_fit` | str | | `footprint` (scale the model to the footprint; default for structures with a model) or `none` |
| `shape`, `weapon`, `roof`, `height`, `scale` | | | placeholder visual hints (`humanoid`, `building`, `mine`, `cart`, `item`, `flyer`; weapon `sword/spear/bow/gun/staff/none`; roof `pyramid/gable`) |
| `notes` | str | | free text, ignored |

### 2.2 `attack`

| Field | Meaning |
|---|---|
| `type` | attack type, key of `combat.attack_types` (`blade, pierce, siege, arcane, heroic, raw, spell`); armour types are `light, medium, heavy, fortified, hero, unarmored, adamant` |
| `damage` | `[min, max]` integer base damage (rolled with `World.rng`) |
| `cooldown` | s between swings, measured from swing start |
| `range` | m, edge to edge (default 0.5) |
| `targets` | `["ground"]`, `["air"]` or both |
| `acquire` | auto-acquire radius; 0 = never acquires or retaliates (workers). Raised to at least `range + 1` (structures: `range`) |
| `damage_point`, `backswing` | s; default from `class_timings[class]` |
| `projectile` | `{speed, arc, model}`; absent/empty = melee |
| `kind` | `melee` / `missile` (derived) or `artillery` (needs `splash`; may have `min_range`, flag `can_attack_ground`) |
| `splash` | `[full, half, quarter]` radii (m) of splash damage falloff |
| `min_range` | m; artillery cannot fire closer |

### 2.3 Unit-only fields (`units.json`)

| Field | Meaning |
|---|---|
| `transform_of`, `transform_duration` | this unit is a transform of another def (Flail Levy of the Hodman), lasting N s |
| `food_from_source` | food is counted on the source unit, not this one (transforms) |
| `lifetime` | summons: seconds until expiry (`Unit.lifetime_ticks`) |
| `trainable` | false for defs never trained (summons, transforms) |
| `family` | creep family (`sootcoats`, `harvest_folk`, `cairnwakes`) |
| `sleeps` | creeps: `night`, `day` or `never` (camp `sleeps_override` wins) |
| `flee_speed`, `startle_radius` | critters |
| `fly_height`, `hover_height` | flyers (m above ground) |
| `brace_time` | artillery set-up time before the first shot |
| `on_death` | `{ground_effect: id}` spawned where the unit dies |
| `active` | creep: ability the AI casts first |

### 2.4 Flags

Movement/targeting: `ground`, `air`, `organic`, `mechanical`, `construct`, `summoned`,
`immobile` (summon that never moves), `invulnerable`, `hardy` (L7 creeps: spell/control
reduction from `rules.creeps`), `hero` (derived defs). Roles: `worker`, `creep`, `critter`,
`item`, `can_attack_ground`. Structures: `structure`, `town_hall`, `dropoff_gold`,
`dropoff_lumber`, `supply`, `altar`, `barracks`, `smithy`, `workshop`, `shop`, `tower`,
`garrison`, `resource`, `gold_mine`, `neutral`, `merchant`, `fountain`, `inn`.
`Unit.has_flag(f)`; `Unit.is_worker/is_hero/is_resource/is_flying/is_item/is_mechanical/is_summoned`
are derived from flags at spawn.

### 2.5 Structure fields (`buildings.json`)

| Field | Meaning |
|---|---|
| `footprint` | `[w, h]` cells (required for structures). Final sizes: halls 16x16, production/tech/shops 12x12, supply 8x8, towers 4x4, gold seam 12x12, Hale Spring 8x8 |
| `tier` | hall tier needed to build (1-3) |
| `food_provided` | food cap added when complete (not while under construction) |
| `trains` | unit/hero ids on the card |
| `research` | upgrade ids researched here |
| `upgrades_to` | building-upgrade ids (each equals its target building id and has an `upgrades.json` entry) |
| `upgrade_of`, `upgrade_only` | the building this one upgrades from; `upgrade_only` = cannot be built directly |
| `rally` | has a rally point (card key R) |
| `blocks_pathing` | default true; false = units walk over it (Hale Spring) |
| `model_addons` | extra model ids drawn with the base (upgraded halls) |
| `model_depleted` | gold seam model once empty |
| `minimap_glyph`, `sign_name` | UI hints |
| `garrison`, `garrison_accepts`, `garrison_attack`, `garrison_eject_hp` | Home Yurt: slots, def ids that may enter, attack while occupied (an `attack` dict), HP fraction at which occupants are ejected |
| `aura` | `{radius, hp_pct_per_s, exclude: [flags]}` (Hale Spring) |
| `gold`, `occupancy` | gold seam: starting gold (the map's `meta.gold_amounts` overrides per mine), workers inside at once |

### 2.6 Hero unit defs (derived)

For each hero in `heroes.json` Defs builds a level-1 unit def with the same id: `kind unit`,
flags `ground, organic, hero`, `hero_id`, stats from `hero_stats(id, 1)`, `hero_abilities`
(the 4 learnable abilities; `abilities` stays empty until learned), sight/acquire/radius from
`rules.heroes`. `HeroSystem.apply_attributes` recomputes them on level-up.

## 3. `heroes.json`

`rules.heroes` (rules.md §6): `max`, `slots_by_tier`, `unique_types`, `cost_gold`,
`cost_lumber`, `food`, `train_time`, `inn_*`, `level_cap`, `xp_levels` (total XP per level),
`skill_points_start`, `skill_points_per_level`, `rank_levels` (hero level needed per rank),
`ultimate_level`, attribute coefficients (`base_hp`, `str_hp`, `str_hp_regen`, `agi_armor`,
`agi_attack_speed`, `int_mana`, `int_mana_regen`, `primary_damage`, `attribute_rounding`),
`control_duration_factor`, `inventory_slots`, `sight [day, night]`, `acquire`, `radius`,
`revive`, `inn_revive`. `rules.xp`: `unit_kill` (XP by level), `hero_kill`, `summon_factor`,
`creep_factor`, `share_radius`, `no_hero_in_range`, `single_hero_bonus`,
`max_level_takes_share`, `structure_kills_give_xp`, `deny_gives_xp`.

`heroes.<id>`:

| Field | Meaning |
|---|---|
| `name`, `title`, `archetype`, `faction` | display / design notes |
| `primary` | `str`, `agi` or `int` (primary attribute adds damage) |
| `attributes` | `{str: [base, growth], agi: [...], int: [...]}` per level |
| `base_damage` | `[min, max]` before the primary bonus |
| `base_armor`, `base_cooldown` | before AGI |
| `range`, `targets`, `projectile`, `speed`, `class`, `attack_type` (`heroic`), `armor_type` (`hero`) | weapon/body |
| `abilities` | exactly 3 normal + 1 ultimate ability ids (validated) |
| `cost`, `first_hero_free`, `hotkey` | altar card |
| `model`, `weapon`, `height` | visuals |
| `proper_names` | picked per spawn |
| `level1_check` | expected level-1 stats from the design doc; `test_data` asserts `hero_stats` matches |

## 4. `abilities.json`

One table for every card entry: commands, hero kits, unit/building abilities, creep abilities.

| Field | Meaning |
|---|---|
| `name` | display name (required) |
| `type` | (required) `target_unit`, `target_point`, `target_unit_or_point`, `instant`, `passive`, `aura`, `toggle`, `command` |
| `effect` | (required) effect id → `src/systems/abilities/effects/<effect>.gd` or `src/systems/items/effects/<effect>.gd` (`EffectRegistry`); `command` for card commands |
| `owner` | `common`, `hero`, `unit`, `building`, `creep` |
| `hero` | owning hero id (hero abilities) |
| `hotkey`, `slot` | card letter; hero ability slot 0-3 |
| `levels` | learnable ranks (heroes 3, ultimates 1) |
| `ultimate` | learnable at `rules.heroes.ultimate_level` |
| `mana`, `cooldown`, `range`, `area`, `duration`, `cast_point`, `cast_backswing`, `channel` | top-level values (rank-independent unless overridden). `range < 0` / missing for instant |
| `targets` | `{relation: [self, self_player, ally, enemy], require: [flags], require_any: [flags], exclude: [flags], exclude_self}` (`CastContext.allows`) |
| `params` | effect parameters (buff ids, damage types, factors, summoned unit ids, `order` for commands) |
| `ranks` | per-rank overrides `[{...}, ...]`, length must equal `levels` |
| `autocast` | `{default: bool, range, prefer, exclude, only_damaged}` |
| `unlock` | upgrade id that unlocks it (Tech.ability_unlocked) |
| `targeting` | for commands: how the card targets (`instant`, `target_point`, `target_unit`, `target_unit_or_point`) |
| `fx`, `ai`, `functional_equivalent` | juice id; AI hint; design note (the ability's role echoes a genre staple, its form is original) |

`Defs.ability_rank(id, rank)` resolves one rank: top-level fields (+ `cast_point`/`cast_backswing`
defaults from `combat.defaults`), then `params`, then `ranks[rank-1]`, plus `rank` and `id`.
Validation: referenced `buff`, `*_buff`, `ground_effect`, `unit`/`summon` and `ability` params
must exist.

Command abilities (`cmd_*`, `type: command`, `params.order` = the order/command type):
`cmd_move, cmd_stop, cmd_hold, cmd_attack, cmd_patrol, cmd_attack_ground, cmd_gather,
cmd_return_cargo, cmd_build_basic, cmd_build_advanced, cmd_learn, cmd_rally`. Unit cards have
fixed letters M S H A P (rules §18.4), heroes O (learn); a building with `rally` uses R.

## 5. `buffs.json`

`rules.status`: `same_buff` (`refresh`), `same_aura` (`highest`), `dot_interval`,
`aura_refresh`, `aura_linger`, `fade_time`, `grounded_speed_factor`, `liftoff_time`.

`buffs.<id>`:

| Field | Meaning |
|---|---|
| `name`, `polarity` (`positive/negative/neutral`), `kind` (`magic/physical/aura/ultimate/passive/item`), `dispellable` | required |
| `duration`, `hero_duration`, `hero_factor` | s; on heroes `hero_duration` or `duration × hero_factor` (`rules.heroes.control_duration_factor` for control) |
| `modifiers` | stat modifiers pushed through `Unit.set_modifiers(&"buffs", ...)`: `armor`, `damage`, `damage_pct`, `attack_speed_pct`, `move_speed_pct`, `hp_regen`, `mana_regen`, `damage_taken_pct`, `miss_chance`, `sight_override`, `max_hp` |
| `status` | statuses. `Unit.STATUS_FLAGS` drive the sim: `stun`, `root`, `silence`, `disarm`, `invulnerable`, `cannot_die`, `hidden`, `invisible`, `sleep`, `taunt`, `ignore_slows`, `no_displace`; other tags (`revealed`, `timed_life`, `ignore_orders`, `transformed`, `hardy`) are read by their systems (`Unit.status`: flag -> true) |
| `periodic` | `{dps, damage_type}` / `{heal_total}` / `{mana_total}` / `duration_key` |
| `on_attack` | `{apply_buff}` / `{line_cleave}` |
| `on_expire` | `{effect}` / `{heal_max_hp_pct}` |
| `on_break_attack` | `{bonus_damage, damage_type}` (breaking invisibility with an attack) |
| `breaks_on`, `condition`, `invisibility`, `fade_time`, `crit`, `structure_factor`, `wake_on_damage` | behaviour switches |

Ability ranks override buff numbers: `BuffSystem.apply(target, id, source, values)` merges
`values` over the def.

`ground_effects.<id>` (persistent areas, `AbilitySystem.add_ground_effect`): `name`, `shape`,
`radius`, `duration`, `linger`, `tick`, `relation`, `require`, `periodic {damage_type,
dps_param}` (`dps_param` names the ability rank value), `impact_damage`, `buff`, `ally_buff`,
`enemy_buff`, `blocks_vision`, `structure_factor`, `damage_type`, `fx`.

## 6. `items.json`

`rules.items`: `pickup_range`, `give_range`, `recall_*`, `group_cooldown {group: s}`,
`charge_merge_factor`, `powerup_any_unit`, `full_inventory`, `flat_xp_ignores_single_hero_bonus`,
`drop_pool_weight_default`.

`items.<id>`:

| Field | Meaning |
|---|---|
| `name`, `class`, `level`, `effect` | required. Class: `purchasable`, `powerup` (used on pickup), `permanent`, `charged`, `artifact` |
| `targeting` | `instant` or `target_point` (slice items); `target_unit` is reserved |
| `range` | use range (m) for targeted items |
| `charges` | initial charges (consumed; 0 = gone) |
| `price` | `{gold, lumber}` (required for purchasable) |
| `value` | sell base (sold at `rules.neutral.sell_factor`) |
| `cooldown`, `cooldown_group` | per-hero cooldown, shared within a group (`rules.items.group_cooldown`) |
| `unique`, `unique_group` | one per hero / per group |
| `params` | effect parameters (`amount`, `buff`, `duration`, `radius`, attribute bonuses `{str, agi, int}`, `armor`, `building`...) |
| `use_on_pickup` | power-ups |
| `drops` | may appear in creep drop pools (class + level) |
| `tags`, `model` | AI/UI tags; ground model (empty = placeholder bundle) |

## 7. `upgrades.json`

`kind: research` (smithy/barracks research) or `kind: building_upgrade` (hall tiers, tower
upgrades; the id equals the target building id).

| Field | Meaning |
|---|---|
| `name`, `kind`, `levels` | required. `levels`: `[{cost {gold, lumber}, time, requires_tier}]`, one per level |
| `faction`, `hotkey`, `summary` | card |
| `building` | research: the building whose card holds it |
| `from`, `to`, `tier` | building upgrade: source and target building ids (`to.upgrade_of == from`), resulting hall tier |
| `requires` | ids needed (e.g. the altar for tier 2) |
| `effects` | `[{type, ...}]`: `upgrade_damage {units}`, `armor {units, amount}`, `range {units, amount}`, `unit_bonus {units, hp, damage, mana, value}`, `unlock_ability {units, ability}`, `splash {units, half}`, `building_bonus {armor, hp_pct, faction}`, `hall_tier {tier}`, `transform_building` |

## 8. `shops.json`

`rules.neutral`: `use_range` (m from footprint edge), `sell_factor`, `stock_per_player`,
`player_unit_bounty`, `buy_needs_hero`, `merc_hire_instant`.

`shops.<building id>`: `owner` (`faction` = tier-gated faction shop, `neutral`), `stock`
`[{item, max, restock (s), from (s of game time), tier, hotkey}]`, `services` [service ids],
`buys_items` (sell factor, 0 = does not buy), `needs_hero`, `hires`, `guarded_by` (camp id).

`services.<id>`: `name`, `kind` (`trade`, `inn_revive`), `hotkey`/`hotkeys`, `give`, `get`,
`cooldown`, `cooldown_group`, `from` (s), `needs_hero`, `taxed_by_upkeep`, `notes`.

## 9. `creep_camps.json`

`rules.creeps` (rules.md §15): acquire radii (`acquire`, `acquire_caster`, `acquire_guard`),
`notice_factor`, `guard_build_radius`, unreachable timers, `leash`, `give_up_time`,
`return_invulnerable`, `return_full_heal`, tower retreat, sleep (`sleep_stagger`,
`wake_trade_radius`, `max_day_camps`, `min_night_sleep_fraction`), `hardy_*`, `raw_level`,
`camp_color_levels`, `bounty {base, per_level, rand}`, `respawn`, `sight [day, night]`,
`ring_radius` (default ring layout), `help_radius`.

`camps.<template id>`:

| Field | Meaning |
|---|---|
| `name`, `tileset`, `colour` (`green/orange/red`), `role` | display / design |
| `creeps` | `[[creep id, count], ...]` |
| `total_level`, `raw_xp` | validated against the creeps' levels and `rules.xp.unit_kill` |
| `avg_bounty_gold` | design check |
| `drops` | `{"A": {class: [item classes], level}, "B": ...}` drop slots |
| `mode` | `camp` or `guard` |
| `sleeps`, `sleeps_override` | sleep schedule for the whole camp |
| `guard_radius`, `guards`, `acquire_override` | guard camps (Smugglers' Den) |
| `layout` | optional `[[dx, dz], ...]` offsets per creep (else a ring of `ring_radius`, highest level in the centre) |

## 10. `factions.json`

- `rules.match`: `start_hour`, `hero_tokens`, `first_hero_recall_grants`, `start_units_idle`,
  `start_worker_spacing`, `main_mine_search_radius`, `cripple_reveal_time`, `defeat_rule`,
  `game_speed`, `map` (map file under `data/maps/`, default `slice`).
- `rules.economy`: `gold_per_trip`, `mine_dwell`, `mine_occupancy`, `mine_gold_main`,
  `mine_gold_expansion`, `mine_low_warning`, `hall_mine_gap` (m), `lumber_per_tree_default`,
  `tree_hp`, `food_cap`, `upkeep_rounding`, `upkeep_taxed_income`, `build_pay`,
  `build_check_on_order`, `build_start_hp`, `build_cancel_refund`, `train_cancel_refund`,
  `research_cancel_refund`, `production_queue`, `shift_train_count`, `repair_cost_factor`,
  `repair_time_factor`, `repair_autocast_range`, `switch_resource_discards_load`,
  `supply_stall_advisory`, `tree_retarget_radius`, `gather_reach`, `dropoff_reach`.
- `rules.regen`, `rules.daynight` (`cycle_length`, `dawn`, `dusk`, `sight_transition`),
  `rules.vision` (`unit/worker/structure [day, night]`, `cap`, `fog_cell`, `fog_update`,
  occluder switches), `rules.minimap`, `rules.controls`, `rules.alerts`, `rules.ai.<easy|normal|hard>`
  (`think_interval` etc., read by `AiPlayer.tuning()`).
- `combat`: `armor_k`, `neg_armor_base`, `attack_types`, `armor_types`, `types`
  (attack × armour multiplier table), `spell_*`, `spectral_multiplier`, speed clamps,
  `range_buffer`, `facing_tolerance`, `structure_target_penalty`, `splash_friendly_fire`,
  `enemy_bodies_solid`, `evasion_stacking`, `crit_stacking`, `proc_mode`, attack reveal,
  `defaults` (acquire, leash, damage_point, backswing, corpse/structure decay, help_radius,
  turn_rate, cast_point, cast_backswing, remains_decay, weapon_kind, alert_interval),
  `class_timings.<class>` (`turn_rate`, `damage_point`, `backswing`).
- `upkeep`: `[{food, gold_factor, label}]` tiers by food used (label = string key).
- `team_colours`: `[{id, hex}]` × 12 (art-bible palette; `PlayerState.colour_for`).
- `factions.<id>`: `name`/`people`/`advisor` (string keys), `worker`, `hall`, `hall_tiers`,
  `altar`, `supply`, `shop`, `heroes`, `lumber_drop`, `start_units {id: n}`, `start_gold`,
  `start_lumber`, `recall_item`, `lumber_per_trip`, `chop_interval`, `fells_trees`,
  `workers_per_tree`, `max_builders`, `extra_builder_rate`, `extra_builder_lumber_per_s`,
  `build_verb`, `build_basic`, `build_advanced` (build menus; hotkeys validated),
  `colour_prefs`, `accent`.

## 11. `doodads.json`

`<tree type>`: `name`, `lumber` per tree, placeholder `shape` (`pine`, `round`) for the tree
types of `MapData.TREE_TYPES` (`tree_pine`, `tree_round`).

## 12. Maps: `data/maps/<name>.json`

Written by `tools/maps/build_slice_map.py` from `data/maps/wether_downs_sketch.txt` and
`docs/design/slice-plan.md` (never hand-edit `slice.json`; rerun the tool). Read by
`MapData.load_json`.

| Key | Meaning |
|---|---|
| `version`, `name`, `width`, `height` | format 1; size in 2 m tiles (slice 96 × 96) |
| `water_level` | m |
| `tex`, `cliff`, `water`, `boundary` | one digit string per tile row: texture layer 0-7, cliff level 0-3, water 0/1, unpathable/unbuildable edge 0/1 |
| `ramps` | `[{rect: [x, z, w, h] tiles, dir: [dx, dz] ascending, low: level}]` |
| `start_locations` | `[[x, y, z]]` hall centres (m) |
| `gold_mines` | `[[x, y, z]]` seam centres; amounts in `meta.gold_amounts` |
| `creep_camps` | `[{id, template (camp id), side (0/1/-1), pos, creeps: [ids], facing, layout?}]` |
| `neutral_buildings` | `[{def, pos, facing (deg)}]` |
| `trees` | `[[x, z, type]]` on the 1 m tree grid (a tree covers 2 × 2 cells) |
| `meta` | `id`, `display_name` (string key), `tileset`, `symmetry` (`mirror_xz`: (x, z) ↔ (z, x)), `hall_footprint_m`, `players`, `neutral_flags`, `gold_amounts`, `starts [{slot, hall, mine, natural, camera}]`, `expansions [{hall, mine, side, guard_camp}]`, `creep_route`, `lanes`, `landmarks {name: [x, z]}`, `critters [{def, pos}]`, `ramp_names` |

## 13. `strings/en.json`

Flat `{key: text}` for UI text that is not an entity name: faction names, advisor lines,
upkeep labels, map names, notifications, menu / pause / end-banner text (`menu_*`, `pause_*`,
`end_*`, `objective_*`, `notify_*`). `Defs.text(key)`.

## 14. `test_defs.json` (tests only)

`units`, `abilities`, `items`, `upgrades`, `factions` sections with `dummy_*` /
`placeholder_*` ids, same schema as the real tables. Loaded only by `Defs.load_test_defs()`
(test runner, sandbox scenario). Gameplay data and `main.gd`'s slice scenario never use them.

## 15. `scenarios.json`

Scripted match set-ups, `{"scenarios": {id: scenario}}`, served by `Defs.scenario(id)` and run
by `BattlefieldScenario` (`src/scenarios/battlefield.gd`; Main's `scenario = "<id>"`). Today:
`battlefield`, Playtest 1 (the Battlefield sandbox). Positions are world metres `[x, z]` on the
scenario's map.

| Field | Meaning |
|---|---|
| `name` | display name (English; the menu label is the string key `menu_<id>`) |
| `map` | map file name under `data/maps/` (`slice`) |
| `victory` | `annihilation`: a player with no living unit or structure is defeated; the match ends when at most one player stands (also the `reason` of `Events.match_ended`) |
| `hero_level` | level every scenario hero starts at (XP, skill points and stats as if earned; abilities unlearned) |
| `think_interval` | s between the scripted opponent's decisions (sim time) |
| `defend_radius` | m: a `guard` group answers enemy units this close to its post or to an own structure |
| `assist_radius` | m: idle group mates within this distance join a member that is fighting |
| `regroup_after` | s without a threat before idle guards walk back to their slots |
| `snap_radius` | m: how far a structure may move from its `pos` to the nearest legal, free spot (`Construction.can_place` + a free 1-cell ring) |
| `formation_spacing` | m between units of a group (default; a group's `spacing` overrides) |
| `camps` | creep camp instance ids of the map to spawn (`CreepSystem.spawn_camps(map, only)`); empty = none |
| `players` | `[{slot, faction, control, structures, groups}]`; `slot` = player id = team; `control`: `human` (the local player, slot 0) or `scenario_ai` (played by the scenario: `PlayerState.is_ai`, no `AiPlayer`) |
| `players[].structures` | `[{def, pos, facing?}]` finished buildings (facing in degrees; default towards the map centre). Validated: `def` is a building |
| `players[].groups` | `[{id, role, pos, face, row, spacing?, units, attack_after?, target?}]`: `units` = `[[def, count], ...]` front row first, laid out in rows of `row` facing the point `face`; validated: mobile unit defs, counts > 0 |
| `role` | `army` (no script), `workers` (idle), `guard` (holds `pos`, defends, assists, regroups), `wave` (waits like a guard, then after `attack_after` s attack-moves at `target` — `hall` = the first enemy structure listed — and keeps hunting the nearest enemy entity) |

