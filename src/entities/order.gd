class_name Order
extends RefCounted
## One queued unit order. Created by World from command dictionaries.

enum Type { MOVE, STOP, HOLD, PATROL, ATTACK, ATTACK_MOVE, SMART, GATHER, BUILD, CAST,
	RALLY, FOLLOW }

const TYPE_NAMES: Dictionary = {
	"move": Type.MOVE, "stop": Type.STOP, "hold": Type.HOLD, "patrol": Type.PATROL,
	"attack": Type.ATTACK, "attack_move": Type.ATTACK_MOVE, "smart": Type.SMART,
	"gather": Type.GATHER, "build": Type.BUILD, "cast": Type.CAST, "rally": Type.RALLY,
	"follow": Type.FOLLOW,
}

var type: Type = Type.MOVE
var target_pos: Vector3 = Vector3.ZERO
var target_id: int = 0            ## 0 = no target unit
var def_id: String = ""
var ability: String = ""
var data: Dictionary = {}
## Shared path of the command this order came from (group moves); null for single units and
## targeted orders. Only the order's first path request uses it.
var group_path: GroupPath = null


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
