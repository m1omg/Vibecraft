class_name CombatFx
extends RefCounted
## Combat impacts (juice bible §3.5, SM-05). Drained from the Vfx queue on the frame after the
## damage tick, never inside it:
##   - victim rim flash (MaterialFlash, latched at its peak; never throttled);
##   - mass-scaled knockback away from the hit's origin (BodyJuice.knock; rings and bars stay);
##   - material x weapon sparks at the contact point (CMB-18): the victim's frontal-arc material
##     for hits from the front (a Pavisier's pavise throws wood splinters, his back plate metal
##     sparks), cone centred on the reflected attack direction, biased 25° up, counts x weapon
##     x tier (FND-3); blunt weapons add a ground dust ring;
##   - first-contact clash (CMB-36): the first melee hit with no melee hit within 6 m in the
##     previous 4 s (≤ 1 per 8 s per 12 m cell) gets sparks x1.3, a dust ring and the clash
##     sound layer, and emits Vfx.battle_started(pos);
##   - layered impact sound through Audio.event (material, weight, kill thock);
##   - deaths: the 60 ms death beat (white held), a death vocal, and the body-fall dust ring
##     and thud when the body lands (Vfx.body_landed from the body composer).
## Missile impacts (sparks at the arrow tip, sticking) are MissileFx's; this adds flash and
## knockback for them. Visual only.

const CELL := 12.0
const CLASH_RADIUS := 6.0
const CLASH_QUIET_S := 4.0
const CLASH_CELL_S := 8.0
const DUST := Color("#B3A48C")

static var gore: bool = true

var vfx: Vfx
var clashes: int = 0
var bursts: int = 0
var _cells: Dictionary = {}          ## Vector2i -> Vector4(x, z, last melee hit fx time, last clash)


func _init(v: Vfx) -> void:
	vfx = v


func on_damage(u: Unit, amount: float, src: Unit) -> void:
	var view := u.view as UnitView
	var killed := not u.alive
	vfx.text.on_damage(u, amount, src)
	if u.is_building or u.is_resource:
		_structure_hit(u, view, amount, src)
		return
	if view != null:
		MaterialFlash.hit(view, amount, u.max_hp, u.is_hero)
	vfx.trace("CMB-17.peak", u.id)
	var melee := src != null and src.projectile.is_empty()
	var origin := src.display_pos() if src != null else Vector3.INF
	var crit := CombatText.is_crit(u, amount, src)
	var ssheet := FxDefs.sheet(src) if src != null else {}
	if view != null and view.juice != null and origin != Vector3.INF:
		var base := float(ssheet.get("knock_m", 0.07)) if melee else float(ssheet.get("ranged_knock_m", 0.05))
		view.juice.knock(origin, amount, u.max_hp, base, crit)
		vfx.trace("CMB-21.impulse", u.id)
	if not melee or src == null:
		return
	var p := u.display_pos()
	if not vfx.allow(p, 3 if (u.is_hero or crit or killed) else 1):
		return
	vfx.hits_this_frame += 1
	var vsheet := FxDefs.sheet(u)
	var facing := u.facing
	var material := FxDefs.hit_material(vsheet, facing, p, origin)
	var to_origin := Vector3(origin.x - p.x, 0.0, origin.z - p.z)
	to_origin = to_origin.normalized() if to_origin.length_squared() > 1e-6 else Vector3(-sin(facing), 0, -cos(facing))
	var contact := p + to_origin * u.radius * 0.9 + Vector3(0.0, u.top_height() * 0.55, 0.0)
	var clash := _clash_check(contact)
	var cone := (to_origin + Vector3.UP * 0.47).normalized()
	var mult := float(ssheet.get("count", 1.0)) * vfx.tier_mult() * (1.3 if clash else 1.0)
	var imp := 3 if (u.is_hero or crit or killed) else 1
	impact_burst(material, contact, cone, mult, imp)
	if bool(ssheet.get("ground_ring", false)):
		vfx.marks.add(GroundMarks.Kind.DUST_RING, Vector3(p.x, 0.0, p.z), 0.2, 0.8,
			Color(DUST, 0.4), 0.15, 0.0, 0.0, null, false)
	if clash:
		clashes += 1
		vfx.marks.add(GroundMarks.Kind.DUST_RING, Vector3(contact.x, 0.0, contact.z), 0.3, 1.2,
			Color(DUST, 0.45), 0.22, 0.0, 0.0, null, false)
		vfx.particles.burst("dust_clash", Vector3(contact.x, p.y + 0.1, contact.z), Vector3.UP, 1.0, 3)
		vfx.trace("CMB-36.clash", u.id)
		vfx.battle_started.emit(contact)
	var heavy := float(ssheet.get("mass", 1.0)) >= 1.5 or str(ssheet.get("weapon", "")) in ["blunt", "chop", "flail"] \
		or bool(ssheet.get("heavy_sound", false))
	Audio.event("melee_hit", contact, {"material": FxDefs.material_sound(material),
		"weight": "h" if heavy else "l", "mass": float(vsheet.get("mass", 1.0)), "kill": killed,
		"clash": clash, "seed": u.id * 31 + vfx.world.tick_count})


## The particle bursts of one impact on `material` (data/fx_units.json materials).
func impact_burst(material: String, pos: Vector3, dir: Vector3, mult: float, importance: int) -> void:
	for b: Array in FxDefs.material_bursts(material):
		var kind := str(b[0])
		if kind == "droplet" and not gore:
			kind = "dust_gore_off"
		var n := float(b[1])
		var amount := float(vfx.particles.kinds.get(kind, {}).get("amount", maxf(n, 1.0)))
		if vfx.particles.burst(kind, pos, dir, clampf(n * mult / maxf(amount, 1.0), 0.0, 1.0), importance):
			bursts += 1


func _structure_hit(u: Unit, view: UnitView, amount: float, src: Unit) -> void:
	if view != null:
		MaterialFlash.structure_hit(view, u.id, amount, u.max_hp)
	if src == null or not src.projectile.is_empty():
		return
	var p := src.display_pos()
	if not vfx.allow(p):
		return
	var c := u.display_pos()
	var to := Vector3(p.x - c.x, 0.0, p.z - c.z).normalized()
	var hit := p - to * src.radius * 1.2 + Vector3(0, 1.0, 0)
	impact_burst(str(FxDefs.sheet(u).get("material", "wood")), hit, (to + Vector3.UP * 0.5).normalized(), 0.6, 1)


## CMB-36 first contact: a melee hit with no melee hit within 6 m in the previous 4 s, and no
## clash in its 12 m cell for 8 s. Records the hit either way.
func _clash_check(pos: Vector3) -> bool:
	var now := FxClock.fx_now
	var cell := Vector2i(floori(pos.x / CELL), floori(pos.z / CELL))
	var quiet := true
	for dz in range(-1, 2):
		for dx in range(-1, 2):
			var c: Variant = _cells.get(cell + Vector2i(dx, dz))
			if c == null:
				continue
			var r: Vector4 = c
			if now - r.z < CLASH_QUIET_S and Vector2(r.x - pos.x, r.y - pos.z).length() <= CLASH_RADIUS:
				quiet = false
	var mine: Vector4 = _cells.get(cell, Vector4(pos.x, pos.z, -100.0, -100.0))
	var clash := quiet and now - mine.w >= CLASH_CELL_S
	_cells[cell] = Vector4(pos.x, pos.z, now, now if clash else mine.w)
	return clash


func on_death(u: Unit, _killer: Unit) -> void:
	var view := u.view as UnitView
	if u.is_building or u.is_resource:
		return
	if view != null:
		MaterialFlash.death_beat(view)
	vfx.trace("CMB-30.beat", u.id)
	var p := u.display_pos() + Vector3(0, u.top_height() * 0.8, 0)
	Audio.event("unit_death", p, {"faction": ViewHooks.faction_of(u), "seed": u.id})


## The body touched the ground (CMB-30 contact): a ring of terrain-coloured dust at the hips
## and the body-fall thud (pitch 1.1 - 0.1·mass).
func on_body_landed(u: Unit, pos: Vector3) -> void:
	var mass := float(FxDefs.sheet(u).get("mass", 1.0))
	vfx.marks.add(GroundMarks.Kind.DUST_RING, Vector3(pos.x, 0.0, pos.z), 0.25, 0.9 + 0.2 * mass,
		Color(DUST, 0.42), 0.45, 0.0, 0.0, null, false)
	vfx.particles.burst("dust_land", pos + Vector3(0, 0.1, 0), Vector3.UP, 1.0, 2)
	vfx.trace("CMB-30.contact", u.id)
	Audio.event("body_fall", pos, {"mass": mass, "armoured": str(FxDefs.sheet(u).get("material", "")) == "metal",
		"seed": u.id})
