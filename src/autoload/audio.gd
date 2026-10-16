extends Node
## Audio facade. Pooled players, bus setup, voice cooldowns. Every call silently no-ops when the
## sound file does not exist, so the game runs with zero audio assets.

const BUSES: Array[String] = ["Music", "SFX", "Voice", "UI", "Ambience"]
const SEARCH_DIRS: Dictionary = {
	"ui": "res://assets/audio/sfx/ui/",
	"sfx": "res://assets/audio/sfx/",
	"voice": "res://assets/audio/voice/",
}
const EXTENSIONS: Array[String] = [".ogg", ".wav", ".mp3"]
const UI_POOL := 4
const WORLD_POOL := 16
const VOICE_COOLDOWN_MS := 900
const ANNOYED_CLICKS := 6

var _ui_players: Array[AudioStreamPlayer] = []
var _voice_player: AudioStreamPlayer
var _world_players: Array[AudioStreamPlayer3D] = []
var _next_ui := 0
var _next_world := 0
var _stream_cache: Dictionary = {}    ## path key -> AudioStream or null (missing)
var _last_voice_ms := -100000
var _voice_clicks := 0


func _ready() -> void:
	_ensure_buses()
	for i in UI_POOL:
		var p := AudioStreamPlayer.new()
		p.bus = "UI"
		add_child(p)
		_ui_players.append(p)
	_voice_player = AudioStreamPlayer.new()
	_voice_player.bus = "Voice"
	add_child(_voice_player)
	for i in WORLD_POOL:
		var p3 := AudioStreamPlayer3D.new()
		p3.bus = "SFX"
		p3.max_distance = 60.0
		add_child(p3)
		_world_players.append(p3)


func play_ui(id: String) -> void:
	var stream := _find_stream("ui", id)
	if stream == null:
		return
	var p := _ui_players[_next_ui]
	_next_ui = (_next_ui + 1) % _ui_players.size()
	p.stream = stream
	p.play()


func play_3d(id: String, pos: Vector3) -> void:
	var stream := _find_stream("sfx", id)
	if stream == null:
		return
	var p := _world_players[_next_world]
	_next_world = (_next_world + 1) % _world_players.size()
	p.stream = stream
	p.global_position = pos
	p.play()


## category: ready | what | yes | attack | annoyed. Rapid repeated "what" clicks escalate to annoyed.
func play_voice(unit: Node, category: String) -> void:
	if unit == null:
		return
	var now := Time.get_ticks_msec()
	if category == "what":
		_voice_clicks = _voice_clicks + 1 if now - _last_voice_ms < 1500 else 1
		if _voice_clicks >= ANNOYED_CLICKS:
			category = "annoyed"
			_voice_clicks = 0
	elif now - _last_voice_ms < VOICE_COOLDOWN_MS:
		return
	var def_id: String = str(unit.get("def_id"))
	var stream := _find_stream("voice", "%s/%s" % [def_id, category])
	if stream == null:
		return
	_last_voice_ms = now
	_voice_player.stream = stream
	_voice_player.play()


func _find_stream(kind: String, id: String) -> AudioStream:
	var key := kind + ":" + id
	if _stream_cache.has(key):
		return _stream_cache[key]
	var found: AudioStream = null
	for ext in EXTENSIONS:
		var path: String = SEARCH_DIRS[kind] + id + ext
		if ResourceLoader.exists(path):
			found = load(path) as AudioStream
			break
	_stream_cache[key] = found
	return found


func _ensure_buses() -> void:
	for bus_name in BUSES:
		if AudioServer.get_bus_index(bus_name) != -1:
			continue
		AudioServer.add_bus()
		var idx := AudioServer.bus_count - 1
		AudioServer.set_bus_name(idx, bus_name)
		AudioServer.set_bus_send(idx, "Master")
