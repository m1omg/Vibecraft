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


## Steps the world `ticks` times and returns each tick's wall time in milliseconds.
func tick_samples(w: World, ticks: int) -> PackedFloat64Array:
	var out := PackedFloat64Array()
	for i in ticks:
		var t0 := Time.get_ticks_usec()
		w.step()
		out.append((Time.get_ticks_usec() - t0) / 1000.0)
	return out


## Time of the calibration workload on the reference machine (4-core Xeon 2.1 GHz, Godot
## 4.7.2 headless) the tick limits below were set on.
const CALIBRATION_REFERENCE_US := 3600.0


## How much slower this machine runs GDScript right now than the reference machine (best of a
## few runs of a fixed workload; never below 1). Shared CI hosts and VMs slow down for seconds
## at a time, so wall-clock limits are scaled by it.
func machine_slowdown() -> float:
	var best := INF
	for r in 5:
		var t0 := Time.get_ticks_usec()
		var acc := 0.0
		var arr: Array = []
		for i in 40000:
			acc += sqrt(float(i)) * 0.5
			arr.append(i)
		arr.clear()
		best = minf(best, float(Time.get_ticks_usec() - t0))
	return maxf(1.0, best / CALIBRATION_REFERENCE_US)


## Builds a fresh scenario with `build` (a Callable returning a World ready to step) `reps`
## times and times `ticks` steps of each. Returns, per tick, the fastest repetition scaled to
## the reference machine. The sim is deterministic, so every repetition does exactly the same
## work: the minimum filters out host noise, a real spike (a path burst) shows in all of them.
func best_tick_samples(build: Callable, ticks: int, reps: int = 3) -> PackedFloat64Array:
	var best := PackedFloat64Array()
	best.resize(ticks)
	best.fill(INF)
	for r in reps:
		var w: World = build.call()
		var k := machine_slowdown()
		var s := tick_samples(w, ticks)
		for i in ticks:
			best[i] = minf(best[i], s[i] / k)
		if r < reps - 1:
			w.free()
	return best


## {avg, p95, max} of tick samples (ms).
func tick_stats(samples: PackedFloat64Array) -> Dictionary:
	var sorted := samples.duplicate()
	sorted.sort()
	var sum := 0.0
	for v in sorted:
		sum += v
	var n := sorted.size()
	return {"avg": sum / maxi(n, 1), "p95": sorted[mini(int(n * 0.95), n - 1)], "max": sorted[n - 1]}


## Asserts the average and the worst tick of a run and prints them.
func assert_tick_cost(samples: PackedFloat64Array, label: String, avg_ms: float, max_ms: float) -> void:
	var st := tick_stats(samples)
	print("     %s: avg %.2f | p95 %.2f | max %.2f ms per tick (%d ticks)" % [label, st["avg"],
		st["p95"], st["max"], samples.size()])
	assert_lt(st["avg"], avg_ms, "%s: average tick" % label)
	assert_lt(st["max"], max_ms, "%s: worst tick" % label)
