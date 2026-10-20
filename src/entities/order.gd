class_name Order
extends RefCounted
## One queued unit order. Created by World from command dictionaries (docs/architecture.md §4).
## Its per-tick behaviour lives in a stateless handler (src/entities/orders/<type>.gd, looked up
## with OrderHandlers.of(type)); per-order state lives here (`target_pos`, `target_id`, `data`).

## Append-only: the numeric values are part of the replay/command contract.
enum Type { MOVE, STOP, HOLD, PATROL, ATTACK, ATTACK_MOVE, SMART, GATHER, BUILD, CAST,
	RALLY, FOLLOW, RETURN_RESOURCES, REPAIR, LEARN, USE_ITEM, PICKUP_ITEM, DROP_ITEM,
	ATTACK_GROUND, ENTER }

## Command "type" strings that become unit orders. Building / player commands (train, cancel,
## research, buy, sell, service, revive, autocast) are routed to systems by World instead.
const TYPE_NAMES: Dictionary = {
	"move": Type.MOVE, "stop": Type.STOP, "hold": Type.HOLD, "patrol": Type.PATROL,
	"attack": Type.ATTACK, "attack_move": Type.ATTACK_MOVE, "smart": Type.SMART,
	"gather": Type.GATHER, "build": Type.BUILD, "cast": Type.CAST, "rally": Type.RALLY,
	"follow": Type.FOLLOW, "return": Type.RETURN_RESOURCES, "return_resources": Type.RETURN_RESOURCES,
	"repair": Type.REPAIR, "learn": Type.LEARN, "use_item": Type.USE_ITEM,
	"pickup_item": Type.PICKUP_ITEM, "drop_item": Type.DROP_ITEM, "give_item": Type.DROP_ITEM,
	"attack_ground": Type.ATTACK_GROUND, "enter": Type.ENTER,
}

var type: Type = Type.MOVE
var target_pos: Vector3 = Vector3.ZERO
var target_id: int = 0            ## 0 = no target unit
var def_id: String = ""           ## build: building def; train-like orders: the def
var ability: String = ""          ## cast / learn: ability id
var slot: int = -1                ## use_item / drop_item: inventory slot (0..5)
## Free-form per-order state for handlers (e.g. "tree": tree index for gather, "phase").
var data: Dictionary = {}
## Shared path of the command this order came from (group moves); null for single units and
## targeted orders. Only the order's first path request uses it.
var group_path: GroupPath = null
## Formation moves (rules §7.10): the group's slowest member speed, which every member keeps to
## until it engages or the order ends, so the group arrives as a front. 0 = the unit's own speed.
var march_speed: float = 0.0


static func make(t: Type, pos: Vector3 = Vector3.ZERO, target: int = 0) -> Order:
	var o := Order.new()
	o.type = t
	o.target_pos = pos
	o.target_id = target
	return o


static func type_from_string(s: String) -> int:
	return TYPE_NAMES.get(s, -1)


func type_name() -> String:
	return Type.keys()[type].to_lower()


func _to_string() -> String:
	return "Order(%s %s #%d)" % [type_name(), target_pos, target_id]
