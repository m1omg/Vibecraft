extends SceneTree
## Headless test runner: godot --headless --path . -s tests/run_tests.gd [-- --filter=<text>]
## Discovers tests/unit/test_*.gd, runs every `test_*` method (coroutines allowed), and fails a
## test on assertion failures or on any engine/script error logged while it ran.
## Everything is loaded at runtime: autoload names are not visible to this script at compile time.

const TEST_DIR := "res://tests/unit/"


class ErrorCounter extends Logger:
	var errors: int = 0
	var last: String = ""

	func _log_error(function: String, file: String, line: int, code: String, rationale: String,
			_editor_notify: bool, error_type: int, _script_backtraces: Array[ScriptBacktrace]) -> void:
		if error_type == ERROR_TYPE_WARNING:
			return
		errors += 1
		last = "%s (%s:%d %s)" % [rationale if not rationale.is_empty() else code, file, line, function]

	func _log_message(_message: String, _error: bool) -> void:
		pass


var _counter := ErrorCounter.new()


func _initialize() -> void:
	OS.add_logger(_counter)
	_run.call_deferred()


func _run() -> void:
	await process_frame
	# placeholder dummy_* defs (data/test_defs.json) exist only for tests
	root.get_node("Defs").call("load_test_defs")
	var filter := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--filter="):
			filter = arg.trim_prefix("--filter=")
	var passed := 0
	var failed: Array[String] = []
	var t0 := Time.get_ticks_msec()
	for file in _test_files():
		var script := load(TEST_DIR + file) as GDScript
		if script == null or not script.can_instantiate():
			failed.append("%s: failed to load" % file)
			print("FAIL %s (script failed to load)" % file)
			continue
		var suite: Object = script.new()
		suite.set("tree", self)
		for m in suite.get_method_list():
			var test_name: String = m["name"]
			if not test_name.begins_with("test_"):
				continue
			if not filter.is_empty() and not (file + "::" + test_name).contains(filter):
				continue
			var ok: bool = await _run_one(suite, file, test_name)
			if ok:
				passed += 1
			else:
				failed.append("%s::%s" % [file, test_name])
		if suite.has_method("cleanup"):
			suite.call("cleanup")
	await process_frame
	var ms := Time.get_ticks_msec() - t0
	print("\n%d passed, %d failed (%.1f s)" % [passed, failed.size(), ms / 1000.0])
	for f in failed:
		print("  FAILED: " + f)
	OS.remove_logger(_counter)
	quit(0 if failed.is_empty() else 1)


func _run_one(suite: Object, file: String, test_name: String) -> bool:
	var errors_before := _counter.errors
	suite.call("reset_failures")
	if suite.has_method("before_each"):
		await suite.call("before_each")
	var t := Time.get_ticks_usec()
	await suite.call(test_name)
	var dt := (Time.get_ticks_usec() - t) / 1000.0
	if suite.has_method("after_each"):
		await suite.call("after_each")
	var failures: Array = suite.get("failures")
	var new_errors := _counter.errors - errors_before
	if new_errors > 0:
		failures.append("%d engine/script error(s) logged, last: %s" % [new_errors, _counter.last])
	if failures.is_empty():
		print("PASS %s::%s (%.1f ms)" % [file, test_name, dt])
		return true
	print("FAIL %s::%s" % [file, test_name])
	for f: String in failures:
		print("     - " + f)
	return false


func _test_files() -> Array[String]:
	var out: Array[String] = []
	var dir := DirAccess.open(TEST_DIR)
	if dir == null:
		return out
	for f in dir.get_files():
		if f.begins_with("test_") and f.ends_with(".gd"):
			out.append(f)
	out.sort()
	return out
