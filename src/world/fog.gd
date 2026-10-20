class_name Fog
extends SimSystem
## Fog of war and vision (owner: agent E; rules.md §11, §14, docs/architecture.md §8; data:
## rules.vision, rules.daynight). Stage: fog (throttled: recompute every rules.vision.fog_update).
## Responsibilities:
##   - per-player grids at rules.vision.fog_cell (1 m): UNEXPLORED (black mask), FOGGED, VISIBLE
##   - sight per unit (day / night values with the 3.2 s transition), cliffs block upward sight,
##     trees occlude (tree base level + 2), flyers ignore occluders, attack reveal, timed reveals
##     (Bronze Window, Signal Shell, wards, flares), detection of invisible units, shared allied
##     vision, structure ghosts, the cripple reveal (rules §14.4)
##   - the local player's L8 texture (0 unexplored, 0.5 fogged, 1 visible) for the terrain /
##     tree / water shaders (World.set_fog_texture) and the minimap
## Signals (Events): fog_updated(pid).
## Called by: Unit / AI target filters (can_see), Construction (is_explored for placement),
##   effects (reveal), HUD / minimap / selection (is_visible, state_at, texture), AiPlayer (it
##   only knows what its own fog shows).
## Stub behaviour: every cell visible and explored (fog off), reveals recorded only.

const UNEXPLORED := 0
const FOGGED := 1
const VISIBLE := 2

var enabled: bool = false
var _reveals: Array[Dictionary] = []   ## {pid, pos, radius, ticks, detect}
var _next_reveal: int = 1


func state_at(_pid: int, _pos: Vector3) -> int:
	return VISIBLE


func is_visible(pid: int, pos: Vector3) -> bool:
	return state_at(pid, pos) == VISIBLE


func is_explored(pid: int, pos: Vector3) -> bool:
	return state_at(pid, pos) != UNEXPLORED


## Can player `pid` see unit `u` (vision + invisibility / detection)? Stub: everything visible
## except hidden units.
func can_see(_pid: int, u: Unit) -> bool:
	return u != null and not u.hidden


## Reveals a circle to `pid` for `duration` seconds (detect: shows invisible units). Returns a
## handle.
func reveal(pid: int, pos: Vector3, radius: float, duration: float, detect: bool = false) -> int:
	var h := _next_reveal
	_next_reveal += 1
	_reveals.append({"handle": h, "pid": pid, "pos": pos, "radius": radius,
		"ticks": maxi(1, roundi(duration * World.TICK_RATE)), "detect": detect})
	return h


func reveals() -> Array[Dictionary]:
	return _reveals


## The player's grid (one byte per fog cell, row-major). Stub: empty.
func grid(_pid: int) -> PackedByteArray:
	return PackedByteArray()


## Fog texture for the shaders / minimap. Stub: null (fog rendering off).
func texture(_pid: int) -> Texture2D:
	return null


func sim_tick(_w: World, _dt: float) -> void:
	var i := _reveals.size() - 1
	while i >= 0:
		_reveals[i]["ticks"] = int(_reveals[i]["ticks"]) - 1
		if int(_reveals[i]["ticks"]) <= 0:
			_reveals.remove_at(i)
		i -= 1
