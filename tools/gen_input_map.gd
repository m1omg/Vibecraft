extends SceneTree
## Regenerates the [input] section of project.godot from Settings.default_actions(), leaving
## every other line untouched. Run: godot --headless --path . -s tools/gen_input_map.gd

const PROJECT := "res://project.godot"


func _initialize() -> void:
	var settings_script: GDScript = load("res://src/autoload/settings.gd")
	var actions: Dictionary = settings_script.default_actions()
	var section := "[input]\n\n"
	for action: String in actions:
		var events: Array = []
		for desc: Dictionary in actions[action]:
			events.append(settings_script.make_event(desc))
		section += "%s=%s\n" % [action, var_to_str({"deadzone": 0.2, "events": events})]
	var text := FileAccess.get_file_as_string(PROJECT)
	var start := text.find("\n[input]\n")
	if start >= 0:
		var end := text.find("\n[", start + 1)
		text = text.substr(0, start + 1) + (text.substr(end + 1) if end >= 0 else "")
	var insert_at := text.find("\n[physics]\n") + 1
	text = text.substr(0, insert_at) + section + "\n" + text.substr(insert_at)
	var f := FileAccess.open(PROJECT, FileAccess.WRITE)
	f.store_string(text)
	f.close()
	print("input map written: %d actions" % actions.size())
	quit(0)
