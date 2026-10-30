class_name MatchRules
extends SimSystem
## Skirmish end conditions (rules §17.1, §14.4; rules.match.defeat_rule "no_structures",
## rules.match.cripple_reveal_time). Stage: ai. Main installs it for skirmishes (the Playtest 1
## battlefield has its own scenario victory). Checked twice a second.
##   - Defeat: a player who owns no structure (finished or under construction; units do not
##     count) is defeated (PlayerState.defeated): their remaining units are removed and their
##     vision ends. Events.notification(pid, "defeated") for each.
##   - Victory: the last team with an undefeated player wins: Events.match_ended(winner,
##     "no_structures") once (winner = that team's lowest player id; -1 when nobody is left).
##   - Cripple: a player without a finished hall starts a countdown (the player is told); at 0
##     every structure of theirs is revealed to every enemy until they finish a hall again
##     (`crippled`, `revealed`). Losing the last hall while another is building still counts.
## Signals: Events.match_ended, Events.notification ("cripple_started", "cripple_revealed",
##   "defeated").

const CHECK_TICKS := 15
const REVEAL_S := 1.0             ## a reveal lasts one check and is renewed while it holds

## The match result once decided: {winner, time}; empty while it runs.
var result: Dictionary = {}
## pid -> world.time the cripple countdown started (no finished hall).
var crippled: Dictionary = {}
## pid -> true while that player's structures are revealed to enemies.
var revealed: Dictionary = {}


func sim_tick(w: World, _dt: float) -> void:
	if not result.is_empty() or w.tick_count % CHECK_TICKS != 0:
		return
	var standing: Dictionary = {}     ## team -> lowest undefeated pid
	for p: PlayerState in w.players:
		if p.is_neutral():
			continue
		if not p.defeated and _structures(w, p.id).is_empty():
			_defeat(w, p)
		if p.defeated:
			continue
		var team := w.team_of(p.id)
		standing[team] = mini(int(standing.get(team, p.id)), p.id)
		_cripple_check(w, p)
	if standing.size() <= 1:
		var winner: int = standing.values()[0] if standing.size() == 1 else -1
		result = {"winner": winner, "time": w.time}
		Events.match_ended.emit(winner, str(Defs.rule("match.defeat_rule", "no_structures")))


func _structures(w: World, pid: int) -> Array[Unit]:
	var out: Array[Unit] = []
	for u in w.unit_list:
		if u.alive and u.player_id == pid and u.is_building:
			out.append(u)
	return out


func _defeat(w: World, p: PlayerState) -> void:
	p.defeated = true
	for u in w.units_of_player(p.id):
		if u.alive:
			w.remove_unit(u)
	Events.notification.emit(p.id, "defeated", Defs.text("notice_defeated"))


## Rules §14.4: no finished hall -> a countdown, then every structure revealed to the enemies.
func _cripple_check(w: World, p: PlayerState) -> void:
	var has_hall := false
	for u in _structures(w, p.id):
		if u.has_flag("town_hall") and not u.under_construction:
			has_hall = true
			break
	if has_hall:
		crippled.erase(p.id)
		revealed.erase(p.id)
		return
	if not crippled.has(p.id):
		crippled[p.id] = w.time
		Events.notification.emit(p.id, "cripple_started", Defs.text("notice_cripple_started")
			% roundi(float(Defs.rule("match.cripple_reveal_time", 120.0))))
		return
	if w.time - float(crippled[p.id]) < float(Defs.rule("match.cripple_reveal_time", 120.0)):
		return
	if not revealed.has(p.id):
		revealed[p.id] = true
		Events.notification.emit(p.id, "cripple_revealed", Defs.text("notice_cripple_revealed"))
	if w.fog == null:
		return
	for e: PlayerState in w.players:
		if e.is_neutral() or e.defeated or not w.is_enemy(e.id, p.id):
			continue
		for u in _structures(w, p.id):
			w.fog.reveal(e.id, u.pos, maxf(u.radius, 2.0) + 1.0, REVEAL_S + CHECK_TICKS * World.DT)


## Seconds left before a crippled player is revealed (-1 = not crippled).
func cripple_left(w: World, pid: int) -> float:
	if not crippled.has(pid):
		return -1.0
	return maxf(0.0, float(Defs.rule("match.cripple_reveal_time", 120.0)) - (w.time - float(crippled[pid])))
