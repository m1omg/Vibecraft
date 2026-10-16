class_name PlayerState
extends RefCounted
## Per-player match state. Economy/production systems mutate it during the tick.

const NEUTRAL_HOSTILE := 12
const NEUTRAL_PASSIVE := 13

const COLORS: Array[Color] = [
	Color(0.12, 0.38, 0.95), Color(0.90, 0.14, 0.10), Color(0.10, 0.75, 0.70),
	Color(0.50, 0.20, 0.80), Color(0.95, 0.85, 0.15), Color(0.95, 0.50, 0.10),
	Color(0.20, 0.80, 0.20), Color(0.95, 0.45, 0.75), Color(0.55, 0.55, 0.55),
	Color(0.50, 0.75, 0.95), Color(0.05, 0.35, 0.20), Color(0.45, 0.25, 0.10),
	Color(0.12, 0.12, 0.12), Color(0.70, 0.70, 0.60),
]

var id: int = 0
var team: int = 0
var faction: String = ""
var color: Color = Color.WHITE
var is_ai: bool = false
var gold: int = 0
var lumber: int = 0
var food_used: int = 0
var food_cap: int = 0
var upkeep_tier: int = 0
var tech: Dictionary = {}
var heroes: Array = []


static func make(pid: int, team_id: int, faction_id: String = "", ai: bool = false) -> PlayerState:
	var p := PlayerState.new()
	p.id = pid
	p.team = team_id
	p.faction = faction_id
	p.is_ai = ai
	p.color = COLORS[pid % COLORS.size()]
	return p


func is_neutral() -> bool:
	return id == NEUTRAL_HOSTILE or id == NEUTRAL_PASSIVE
