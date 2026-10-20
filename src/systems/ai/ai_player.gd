class_name AiPlayer
extends SimSystem
## Computer opponent for one player (owner: agent H; rules.md §19, data: rules.ai.<difficulty>,
## faction build orders kingdom.md §10 / clans.md §10, map meta.creep_route). Stage: ai.
## World installs one per AI player (World.add_player(..., ai = true)).
## Responsibilities:
##   - thinking every think_interval (1.0 / 0.5 / 0.5 s) with a reaction delay and an APM cap;
##     the faction opening script, then Build up -> Creep -> Tier up -> Army -> Push / Defend
##   - issuing ONLY the same command dictionaries as the player (World.issue): no cheats, its
##     own fog only (Fog.can_see / is_visible), every rule obeyed
##   - creeping along the map's authored creep route, contested-camp rule, retreat / revive /
##     recall item use, faction signatures (Levy Horn, Sound the Gong), upkeep discipline
##   - its own random stream `rng` (seeded from the match seed ^ 0xA1, rules §2.3) so AI choices
##     never shift combat rolls
## Signals: none (it acts through commands; debug overlays read `state`).

var player_id: int = -1
var difficulty: String = "normal"
var rng := RandomNumberGenerator.new()
var state: String = "build_up"    ## build_up | creep | tier_up | army | push | defend
var _next_think: int = 0


func setup_player(w: World, pid: int, diff: String = "normal") -> void:
	setup(w)
	player_id = pid
	difficulty = diff
	rng.seed = int(w.rng.seed) ^ 0xA1 ^ (pid * 7919)


## Tuning row for this difficulty (rules.ai.<difficulty>).
func tuning() -> Dictionary:
	return Defs.rule("ai." + difficulty, {})


func sim_tick(w: World, _dt: float) -> void:
	if w.tick_count < _next_think:
		return
	_next_think = w.tick_count + maxi(1, roundi(float(tuning().get("think_interval", 0.5)) * World.TICK_RATE))
	think()


## One decision step. Stub: does nothing (the AI agent fills it in).
func think() -> void:
	pass
