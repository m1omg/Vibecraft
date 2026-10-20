class_name SimSystem
extends Node
## Base class of the gameplay systems World installs (docs/architecture.md §4, docs/m2-ownership.md).
##
## World creates every system in World.setup(), calls setup(world), registers it for its stage
## (World.SYSTEM_STAGES) and keeps a typed reference (world.economy, world.production ...).
## Gameplay runs only in sim_tick(world, dt) (fixed 30 Hz) and in the hooks below, which World
## calls synchronously inside the tick, in installation order (deterministic):
##   on_unit_spawned(u)            after World.spawn_unit placed a unit
##   on_unit_died(u, killer)       in the cleanup stage, when a dead unit leaves the sim
##   on_unit_removed(u)            a unit left the sim without dying (World.remove_unit)
##   on_unit_damaged(u, amount, src)  right after Unit.take_damage changed HP
## A system receives a hook only if hooks() lists it (keeps per-hit dispatch cheap).
## handle_command(cmd, units) receives the building / player commands World routes to it
## (World.SYSTEM_COMMANDS); `units` are the command's living units owned by cmd.player.
## Systems never read wall-clock time or frame delta and draw randomness only from world.rng
## (or a seeded stream of their own: AI, critters). Visual juice listens to Events instead.

var world: World


func setup(w: World) -> void:
	world = w


func sim_tick(_w: World, _dt: float) -> void:
	pass


## Hook names this system wants: any of &"spawned", &"died", &"removed", &"damaged".
func hooks() -> Array[StringName]:
	return []


func on_unit_spawned(_u: Unit) -> void:
	pass


func on_unit_died(_u: Unit, _killer: Unit) -> void:
	pass


func on_unit_removed(_u: Unit) -> void:
	pass


func on_unit_damaged(_u: Unit, _amount: float, _src: Unit) -> void:
	pass


## Building / player command routed by World (true = handled).
func handle_command(_cmd: Dictionary, _units: Array[Unit]) -> bool:
	return false
