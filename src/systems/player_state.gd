class_name PlayerState
extends RefCounted
## Per-player match state. Economy/production systems mutate it during the tick.

const NEUTRAL_HOSTILE := 12
const NEUTRAL_PASSIVE := 13

## Our 12 team colours in our own order (art-and-audio bible §2.4; factions.json team_colours),
## then the two neutral players (12 hostile, 13 passive). Slot assignment by faction preference
## (factions.<id>.colour_prefs) is the lobby's job; by default slot i gets COLORS[i].
const COLORS: Array[Color] = [
	Color8(0xD8, 0x23, 0x2A), Color8(0x28, 0x5D, 0xE6), Color8(0xE6, 0xBB, 0x17),
	Color8(0x2E, 0xAE, 0x3A), Color8(0xE3, 0x5F, 0x18), Color8(0x7A, 0x2F, 0xD0),
	Color8(0x5A, 0x92, 0xE6), Color8(0xA8, 0xD4, 0x1E), Color8(0x14, 0xB8, 0xA6),
	Color8(0xE0, 0x50, 0x7A), Color8(0xB0, 0xA6, 0xD6), Color8(0x2A, 0x8C, 0x4A),
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
var heroes: Array = []           ## hero unit ids in acquisition order (HeroSystem; dead heroes stay)
var tier: int = 1                ## hall tier (Tech keeps it current)
var upgrades: Dictionary = {}    ## research / upgrade id -> level reached (Tech)
var hero_tokens: int = 0         ## free heroes left (rules.match.hero_tokens; HeroSystem)
var recall_grants: int = 0       ## first-hero recall items still to grant (rules.match)
var defeated: bool = false


static func make(pid: int, team_id: int, faction_id: String = "", ai: bool = false) -> PlayerState:
	var p := PlayerState.new()
	p.id = pid
	p.team = team_id
	p.faction = faction_id
	p.is_ai = ai
	p.color = COLORS[pid % COLORS.size()]
	p.hero_tokens = int(Defs.rule("match.hero_tokens", 1)) if pid < NEUTRAL_HOSTILE else 0
	p.recall_grants = int(Defs.rule("match.first_hero_recall_grants", 1)) if pid < NEUTRAL_HOSTILE else 0
	return p


## Picks the default colour for `faction_id` in lobby order: the first colour on the faction's
## preference list (factions.<id>.colour_prefs, ids from factions.json team_colours) that no one in
## `taken` holds, else the lowest free one (art-and-audio bible §2.4).
static func colour_for(faction_id: String, taken: Array) -> Color:
	var ids: Array = []
	for c: Dictionary in Defs.team_colours:
		ids.append(str(c.get("id", "")))
	for pref: Variant in Defs.faction(faction_id).get("colour_prefs", []) if faction_id != "" else []:
		var i := ids.find(str(pref))
		if i >= 0 and i < COLORS.size() and not taken.has(COLORS[i]):
			return COLORS[i]
	for i in 12:
		if not taken.has(COLORS[i]):
			return COLORS[i]
	return COLORS[0]


func is_neutral() -> bool:
	return id == NEUTRAL_HOSTILE or id == NEUTRAL_PASSIVE
