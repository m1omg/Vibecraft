extends RefCounted
## Base class for test suites (extend with `extends "res://tests/test_case.gd"`).

var tree: SceneTree
var failures: Array[String] = []
var _nodes: Array[Node] = []


func reset_failures() -> void:
	failures.clear()


func fail(msg: String) -> void:
	failures.append(msg)


func assert_true(cond: bool, msg: String = "expected true") -> bool:
	if not cond:
		fail(msg)
	return cond


func assert_false(cond: bool, msg: String = "expected false") -> bool:
	return assert_true(not cond, msg)


func assert_eq(actual: Variant, expected: Variant, msg: String = "") -> bool:
	if actual != expected:
		fail("%s expected %s, got %s" % [msg, str(expected), str(actual)])
		return false
	return true


func assert_near(actual: float, expected: float, eps: float, msg: String = "") -> bool:
	if absf(actual - expected) > eps:
		fail("%s expected %f +- %f, got %f" % [msg, expected, eps, actual])
		return false
	return true


func assert_lt(a: float, b: float, msg: String = "") -> bool:
	if not a < b:
		fail("%s expected %f < %f" % [msg, a, b])
		return false
	return true


## Keeps a node alive for the test and frees it in cleanup().
func track(n: Node) -> Node:
	_nodes.append(n)
	return n


func cleanup() -> void:
	for n in _nodes:
		if is_instance_valid(n):
			n.free()
	_nodes.clear()


func after_each() -> void:
	cleanup()


## Flat map of w x h tiles at one cliff level (no trees).
func flat_map(w: int = 32, h: int = 32, level: int = 0) -> MapData:
	var m := MapData.new()
	m.init_empty(w, h, level, 0)
	return m


## Headless world (no visuals, manual ticking) with players 0 and 1 on different teams.
func make_world(m: MapData = null, visuals: bool = false) -> World:
	var w := World.new()
	w.auto_tick = false
	w.visuals = visuals
	tree.root.add_child(w)
	track(w)
	w.setup(m if m != null else flat_map())
	w.add_player(0, 0)
	w.add_player(1, 1)
	return w


## Steps the world (at least once, so queued commands apply) until all units are idle.
## Returns the number of ticks taken.
func run_until_idle(w: World, units: Array, max_ticks: int) -> int:
	w.step()
	for t in range(1, max_ticks):
		var busy := false
		for u: Unit in units:
			if u.current != null:
				busy = true
				break
		if not busy:
			return t
		w.step()
	return max_ticks
