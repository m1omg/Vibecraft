class_name OrderHandler
extends RefCounted
## Base class of every order type's behaviour (docs/architecture.md §5 "Orders").
##
## One stateless instance per order type is shared by every unit (OrderHandlers.of(type)), so a
## handler never stores per-unit or per-order state in itself: it reads and writes the Order
## (`target_pos`, `target_id`, `def_id`, `ability`, `slot`, `data`) and the unit's movement and
## combat state through the Unit "handler API" (follow_path, begin_move, fight, chase_move, ...).
##
## Lifecycle, all inside the fixed 30 Hz tick (never _process):
##   can_start(u, o)  on issue. false = the order is dropped (not queued, not made current).
##   enter(u, o)      the order became the unit's current order (start moving, reset state).
##   tick(u, o, dt)   every tick while current; returns the desired velocity (m/s, XZ).
##                    Call u.finish_order() when done: the next queued order starts at once.
##   exit(u, o)       the order stopped being current: finished, replaced by a new order,
##                    STOP, or the unit died. Release whatever enter() reserved.
##   accepts_retaliation(u, o)  true: a hit makes the unit fight back (then resume).
##   is_instant()     true: the order is applied on issue by apply_instant() and never becomes
##                    current or queued (e.g. learn).
##   allows_immobile() true: structures / immobile summons accept the order too.
## Handlers may call any public Unit method and the World systems (u.world.economy, ...).


func can_start(_u: Unit, _o: Order) -> bool:
	return true


func enter(_u: Unit, _o: Order) -> void:
	pass


func tick(_u: Unit, _o: Order, _dt: float) -> Vector3:
	return Vector3.ZERO


func exit(_u: Unit, _o: Order) -> void:
	pass


func accepts_retaliation(_u: Unit, _o: Order) -> bool:
	return false


func is_instant() -> bool:
	return false


func apply_instant(_u: Unit, _o: Order) -> void:
	pass


func allows_immobile() -> bool:
	return false
