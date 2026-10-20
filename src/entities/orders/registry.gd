class_name OrderHandlers
extends RefCounted
## Order.Type -> shared, stateless OrderHandler instance (src/entities/orders/<type>.gd).
## Adding an order type: append it to Order.Type and Order.TYPE_NAMES, write its handler, map it
## here, and route its command in World (docs/architecture.md §4).

const SCRIPTS: Dictionary = {
	Order.Type.MOVE: preload("res://src/entities/orders/move.gd"),
	Order.Type.STOP: preload("res://src/entities/orders/stop.gd"),
	Order.Type.HOLD: preload("res://src/entities/orders/hold.gd"),
	Order.Type.PATROL: preload("res://src/entities/orders/patrol.gd"),
	Order.Type.ATTACK: preload("res://src/entities/orders/attack.gd"),
	Order.Type.ATTACK_MOVE: preload("res://src/entities/orders/attack_move.gd"),
	Order.Type.SMART: preload("res://src/entities/orders/move.gd"),      # resolved before issue
	Order.Type.GATHER: preload("res://src/entities/orders/gather.gd"),
	Order.Type.BUILD: preload("res://src/entities/orders/build.gd"),
	Order.Type.CAST: preload("res://src/entities/orders/cast.gd"),
	Order.Type.RALLY: preload("res://src/entities/orders/stop.gd"),      # never current (Unit.issue_order)
	Order.Type.FOLLOW: preload("res://src/entities/orders/follow.gd"),
	Order.Type.RETURN_RESOURCES: preload("res://src/entities/orders/return_resources.gd"),
	Order.Type.REPAIR: preload("res://src/entities/orders/repair.gd"),
	Order.Type.LEARN: preload("res://src/entities/orders/learn.gd"),
	Order.Type.USE_ITEM: preload("res://src/entities/orders/use_item.gd"),
	Order.Type.PICKUP_ITEM: preload("res://src/entities/orders/pickup_item.gd"),
	Order.Type.DROP_ITEM: preload("res://src/entities/orders/drop_item.gd"),
	Order.Type.ATTACK_GROUND: preload("res://src/entities/orders/attack_ground.gd"),
	Order.Type.ENTER: preload("res://src/entities/orders/enter.gd"),
}
const IDLE_SCRIPT := preload("res://src/entities/orders/idle.gd")

static var _handlers: Dictionary = {}
static var _idle: OrderHandler = null


static func of(t: int) -> OrderHandler:
	var h: OrderHandler = _handlers.get(t)
	if h == null:
		h = (SCRIPTS[t] as GDScript).new()
		_handlers[t] = h
	return h


## The no-order behaviour (auto-acquire, leash, creep return, tower fire).
static func idle() -> OrderHandler:
	if _idle == null:
		_idle = IDLE_SCRIPT.new()
	return _idle
