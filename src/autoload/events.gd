extends Node
## Global event bus. Gameplay code emits; UI/audio/fx listen. Arguments are typed loosely
## (Node / Object) where the concrete class lives outside the autoload to avoid load cycles.

signal unit_spawned(u: Node)
signal unit_died(u: Node, killer: Node)
signal unit_damaged(u: Node, amount: float, src: Node)
signal order_issued(u: Node, order: RefCounted)
signal building_completed(u: Node)
signal training_completed(building: Node, unit: Node)
signal resources_changed(player_id: int)
signal hero_level_up(u: Node)
signal research_completed(player_id: int, id: String)
signal selection_changed(units: Array)
signal notification(player_id: int, kind: String, text: String)

# Additions to the architecture contract (see docs/architecture.md §5).
signal alert_raised(player_id: int, pos: Vector3)   ## space bar jumps to the latest one
signal tree_felled(pos: Vector3)
signal command_issued(command: Dictionary)
signal menu_requested
