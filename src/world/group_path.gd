class_name GroupPath
extends RefCounted
## One shared path search for the units of a single ground command (move, attack-move, patrol).
## The first unit that needs a path runs a normal (budgeted) query and offers the result as a
## base; group members whose formation slot starts near that base derive their path from it
## with a few line checks instead of their own A* query:
## 1. shifted: the base waypoints moved by the difference between the two goals (the formation
##    offset; zero when everyone heads for the same point); a waypoint whose shifted point is
##    not in straight walking reach takes half the offset or none (the group narrows only at
##    chokepoints and opens out again after them);
## 2. joined: otherwise the base waypoints themselves, entered at one of the first JOIN_TRIES
##    waypoints in straight reach and left for the unit's own goal at the end.
## A unit whose path fits neither runs its own query, which becomes another base. A group order
## therefore costs a few A* queries instead of one per unit. Deterministic: bases are created
## in unit tick order, and the line checks are charged to the pathing budget.

const SHARE_RADIUS := 12.0       ## a base is used only if it started this close to the unit's slot
const SNAPPED_EPS := 0.75        ## a base ending further than this from its goal was snapped
const CHECK_COST := 0.2          ## path budget per cell of checked segment (measured: a line
                                 ## check costs ~1/5 of a query per cell; see Pathing.estimate_cost)
const MAX_BASES := 16
const JOIN_TRIES := 3
## Share of the formation offset tried per waypoint, widest first (0 = the base waypoint).
const SHIFT_STEPS: Array[float] = [1.0, 0.5, 0.0]
const MAX_CHECKS_PER_WAYPOINT := 4   ## line-check allowance of one shifted derivation


class Base:
	var path: PackedVector3Array
	var goal: Vector3
	var large: bool


var _bases: Array[Base] = []
var _checked: float = 0.0        ## metres of line checks in the current derive()


## Offers a unit's own query result as a base for the rest of the group.
func add_base(path: PackedVector3Array, goal: Vector3, large: bool) -> void:
	if path.size() < 2 or _bases.size() >= MAX_BASES:
		return
	var b := Base.new()
	b.path = path
	b.goal = Vector3(goal.x, 0.0, goal.z)
	b.large = large
	_bases.append(b)


## Base whose start, shifted into this unit's formation slot, is closest to `from` (within
## SHARE_RADIUS), or null.
func find_base(from: Vector3, goal: Vector3, large: bool) -> Base:
	var best: Base = null
	var best_d := SHARE_RADIUS
	for b in _bases:
		if b.large != large or b.path.size() < 2:
			continue          # a base its owner has since emptied is no use to anyone
		var s := b.path[0]
		var d := Vector2(s.x + goal.x - b.goal.x - from.x, s.z + goal.z - b.goal.z - from.z).length()
		if d <= best_d:
			best_d = d
			best = b
	return best


## Path from `from` to `goal` along base `b` (y = 0, like Pathing.find_path), or empty when
## neither the shifted nor the joined variant fits.
func derive(pathing: Pathing, b: Base, from: Vector3, goal: Vector3) -> PackedVector3Array:
	_checked = 0.0
	var last := _end_for(pathing, b, goal)
	var out := _shifted(pathing, b, from, goal, last)
	if out.is_empty():
		# without a formation offset the shifted variant already tried the first waypoint
		var same := Vector2(goal.x - b.goal.x, goal.z - b.goal.z).length_squared() < 1e-6
		out = _joined(pathing, b, from, last, 2 if same else 1)
	pathing.charge(_checked / Grid.CELL * CHECK_COST)
	return out


## Where this unit's path ends: its own goal when the base reached its goal and the unit's goal
## is walkable, else the base end (the goal is unreachable; the unit cannot get closer either).
func _end_for(pathing: Pathing, b: Base, goal: Vector3) -> Vector3:
	var end := b.path[b.path.size() - 1]
	var own := Vector3(goal.x, 0.0, goal.z)
	if Grid.flat_dist(end, b.goal) <= SNAPPED_EPS and pathing.is_walkable_world(own, b.large):
		return own
	return end


func _check(pathing: Pathing, a: Vector3, c: Vector3, large: bool) -> bool:
	_checked += Grid.flat_dist(a, c)
	return pathing.line_of_walk(a, c, large)


## The base waypoints moved by the formation offset, so the group marches as a front on
## parallel lanes. Where a shifted waypoint cannot be walked to in a straight line (a ramp, a
## gap in a tree line, the snapped end at a building), that waypoint takes a smaller share of
## the offset (SHIFT_STEPS, down to the base waypoint itself), backtracking to narrow the
## previous waypoint when nothing fits: the group narrows only at the chokepoint and opens out
## again after it. Base segments between two unshifted waypoints are known to be walkable, so
## the search always ends (at worst on the base lane) once the first leg is walkable. Empty
## when it is not, or when the search runs out of its check allowance.
func _shifted(pathing: Pathing, b: Base, from: Vector3, goal: Vector3, last: Vector3) -> PackedVector3Array:
	var base := b.path
	var n := base.size()
	var shift := Vector3(goal.x - b.goal.x, 0.0, goal.z - b.goal.z)
	var steps: Array[float] = SHIFT_STEPS if shift.length_squared() >= 1e-6 else ([0.0] as Array[float])
	var start := Vector3(from.x, 0.0, from.z)
	var choice := PackedInt32Array()
	choice.resize(n)
	var pts := PackedVector3Array()
	pts.resize(n)
	pts[0] = start
	var checks := 0
	var limit := n * MAX_CHECKS_PER_WAYPOINT
	var k := 1
	while k < n:
		var options := 1 if k == n - 1 else steps.size()
		if choice[k] >= options:
			if k == 1:
				return PackedVector3Array()
			choice[k] = 0
			k -= 1
			choice[k] += 1
			continue
		var f: float = 0.0 if k == n - 1 else steps[choice[k]]
		var want := last if k == n - 1 else base[k] + shift * f
		var prev_on_base := k > 1 and steps[choice[k - 1]] == 0.0
		var known := prev_on_base and (want.is_equal_approx(base[k]))
		if not known:
			checks += 1
			if checks > limit:
				return PackedVector3Array()
		if known or _check(pathing, pts[k - 1], want, b.large):
			pts[k] = want
			k += 1
			if k < n:
				choice[k] = 0
		else:
			choice[k] += 1
	return pts


func _joined(pathing: Pathing, b: Base, from: Vector3, last: Vector3, first: int) -> PackedVector3Array:
	var base := b.path
	var n := base.size()
	var out := PackedVector3Array()
	out.append(Vector3(from.x, 0.0, from.z))
	var join := -1
	for k in range(first, mini(n - 1, JOIN_TRIES + 1)):
		if _check(pathing, out[0], base[k], b.large):
			join = k
			break
	if join < 0:
		return PackedVector3Array()
	for k in range(join, n - 1):
		out.append(base[k])
	if not last.is_equal_approx(base[n - 1]) and not _check(pathing, base[n - 2], last, b.large):
		return PackedVector3Array()
	out.append(last)
	return out
