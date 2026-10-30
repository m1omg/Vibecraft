extends Node
## Global event bus. Gameplay code emits (inside the fixed tick); UI, audio, juice and fx listen.
## Arguments are typed loosely (Node / Object) where the concrete class lives outside the autoload
## to avoid load cycles. Listeners must never change sim state (juice never changes outcomes).
## Systems talk to each other through World hooks and their APIs, not through these signals
## (several Worlds can exist at once in tests). Owners per group: docs/m2-ownership.md.

signal unit_spawned(u: Node)
signal unit_died(u: Node, killer: Node)
## A unit left the sim without dying (World.remove_unit: a cancelled site, a picked-up item, a
## defeated player's units); it is freed at the end of the tick.
signal unit_removed(u: Node)
signal unit_damaged(u: Node, amount: float, src: Node)
signal order_issued(u: Node, order: RefCounted)
signal building_completed(u: Node)
signal training_completed(building: Node, unit: Node)
signal resources_changed(player_id: int)
signal hero_level_up(u: Node)
signal research_completed(player_id: int, id: String)
signal selection_changed(units: Array)
signal notification(player_id: int, kind: String, text: String)

# Additions to the architecture contract (see docs/architecture.md §5).
signal alert_raised(player_id: int, pos: Vector3)   ## space bar jumps to the latest one
signal tree_felled(pos: Vector3)
signal command_issued(command: Dictionary)
signal menu_requested

# --- M2 system events (docs/architecture.md §4, docs/m2-ownership.md) ----------------------
# economy (A)
signal income_received(player_id: int, kind: String, amount: int, pos: Vector3)
signal upkeep_changed(player_id: int, tier: int)
signal cargo_delivered(worker: Node, building: Node, kind: String, amount: int)
signal mine_low(mine: Node)
signal mine_depleted(mine: Node)
# construction (A)
signal construction_started(site: Node, builder: Node)
signal construction_cancelled(site: Node)
signal repair_started(worker: Node, target: Node)
signal placement_rejected(player_id: int, def_id: String, reason: String)
signal garrison_changed(building: Node)
# production / tech (B)
signal training_started(building: Node, def_id: String)
signal queue_changed(building: Node)
signal production_stalled(building: Node, reason: String)
signal research_started(player_id: int, id: String, building: Node)
signal tier_changed(player_id: int, tier: int)
## A building became its upgrade in place (Tech: hall tiers, tower upgrades); views reload.
signal building_upgraded(building: Node, from_def: String)
# heroes / abilities / buffs (C)
signal xp_gained(hero: Node, amount: float)
signal ability_learned(hero: Node, ability_id: String, rank: int)
signal hero_died(hero: Node)
signal hero_revived(hero: Node)
## Kill XP reached a hero (HeroSystem.award_kill_xp): the amount, where the victim fell and how
## many levels it crossed (the XP motes fly from there, juice HER-03).
signal hero_xp_gained(hero: Node, amount: float, from_pos: Vector3, levels: int)
signal ability_cast(caster: Node, ability_id: String, rank: int, target: Node, pos: Vector3)
## An attack missed (the attacker's miss_chance, e.g. blinded; Combat.fire): no damage, a "miss" tell.
signal attack_missed(attacker: Node, target: Node)
## A unit changed its def in place (Take Up / Lay Down the Flail): its view reloads.
signal unit_transformed(unit: Node, from_def: String)
## A recall finished: the hero (and `count` - 1 others) arrived beside `hall`.
signal recall_completed(hero: Node, hall: Node, count: int)
## A spell or item healed `amount` HP (the heal number and bloom).
signal unit_healed(unit: Node, amount: float, source: Node)
## A delayed ability blast went off (Fuse Mark's explosion): its id, where, its splash radius.
signal ability_burst(ability_id: String, pos: Vector3, radius: float)
signal cast_started(caster: Node, ability_id: String)
signal cast_cancelled(caster: Node, ability_id: String)
signal autocast_changed(unit: Node, ability_id: String, on: bool)
signal ground_effect_added(handle: int, effect_id: String, pos: Vector3, radius: float)
signal buff_applied(unit: Node, buff_id: String)
signal buff_removed(unit: Node, buff_id: String)
signal dispelled(unit: Node, count: int)
# items / shops / creeps (D)
signal item_picked_up(unit: Node, item_id: String)
signal item_dropped(unit: Node, item_id: String, pos: Vector3)
signal item_used(unit: Node, item_id: String)
signal inventory_changed(unit: Node)
signal item_bought(player_id: int, shop: Node, item_id: String, hero: Node)
signal item_sold(player_id: int, shop: Node, item_id: String)
signal stock_changed(player_id: int, shop: Node)
signal service_used(player_id: int, shop: Node, service_id: String)
signal camp_aggro(camp_id: String)
signal camp_cleared(camp_id: String)
signal camp_slept(camp_id: String)
signal camp_woke(camp_id: String)
signal bounty_paid(player_id: int, amount: int, pos: Vector3)
# fog (E)
signal fog_updated(player_id: int)
# match / scenarios (src/scenarios/*: scripted set-ups such as the Playtest 1 battlefield)
## The match is decided (juice SEQ-02 listens): winning player id (1v1: = its team), -1 when
## nobody is left; reason e.g. "annihilation".
signal match_ended(winner: int, reason: String)
