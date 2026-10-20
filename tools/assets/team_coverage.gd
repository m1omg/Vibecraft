extends RefCounted
## Team-colour coverage of a unit model as the player sees it (art bible §3.1 rules 1 and 2).
##
## A small software rasteriser draws the model's rest pose from the game camera (pitch −56°,
## orthographic, eight yaws around the unit) with a depth buffer, and for every visible pixel
## evaluates the same team weight the unit shader uses (team_mode 2: the per-texel mask
## `<model>_team.png` through smoothstep(0.45, 0.8) plus the magenta key on the albedo). It
## reports:
##   coverage     team weight / silhouette pixels (the bible's "share of the visible silhouette")
##   upper        team weight in the upper third of the model height / silhouette pixels
##   texel        plain mask texel share (>= 128), the number QA measured from the PNG
## No autoloads: the CLI (check_team_coverage.gd) classifies models through Defs.
## Visual tooling only; nothing here touches the simulation.

const PITCH_DEG := -56.0
const YAWS := 8
const RES := 160
## Bible §3.1 rule 1: 10–15 % of the visible silhouette; workers at least 8 %, heroes at most 18 %.
const LIMITS := {"unit": Vector2(0.10, 0.15), "worker": Vector2(0.08, 0.15), "hero": Vector2(0.10, 0.18)}
## Rule 2: some team colour in the upper third (hat band, plume, streamer, mantle). A model passes
## when at least this share of its silhouette is team colour above two thirds of its height.
const UPPER_MIN := 0.005

## Set to an Image to get the last rasterised view drawn into it (debugging: silhouette grey,
## team weight green, upper third lighter).
static var debug_image: Image = null


static func limits(kind: String) -> Vector2:
	return LIMITS.get(kind, LIMITS["unit"])


## {ok, problems: Array[String]} for a measurement (see measure_model) of a `kind` model.
static func verdict(m: Dictionary, kind: String) -> Dictionary:
	var lim := limits(kind)
	var problems: Array[String] = []
	var cov := float(m.get("coverage", 0.0))
	if cov < lim.x - 0.0005:
		problems.append("coverage %.1f %% < %.0f %%" % [cov * 100.0, lim.x * 100.0])
	elif cov > lim.y + 0.0005:
		problems.append("coverage %.1f %% > %.0f %%" % [cov * 100.0, lim.y * 100.0])
	if float(m.get("upper", 0.0)) < UPPER_MIN:
		problems.append("no team area in the upper third (%.2f %%)" % (float(m.get("upper", 0.0)) * 100.0))
	return {"ok": problems.is_empty(), "problems": problems}


## Measures a unit GLB (its `<basename>_team.png` mask and its albedo texture).
static func measure_model(glb_path: String) -> Dictionary:
	var ps := load(glb_path) as PackedScene
	if ps == null:
		return {}
	var root := ps.instantiate() as Node3D
	var mask_path := glb_path.get_basename() + "_team.png"
	var mask: Image = null
	if FileAccess.file_exists(mask_path):
		mask = Image.load_from_file(ProjectSettings.globalize_path(mask_path))
	var pos := PackedVector3Array()
	var uv := PackedVector2Array()
	var idx := PackedInt32Array()
	var albedo: Image = null
	for mi: MeshInstance3D in root.find_children("*", "MeshInstance3D", true, false):
		if mi.mesh == null:
			continue
		var xf := Transform3D.IDENTITY
		var c: Node = mi
		while c != null and c != root:
			if c is Node3D:
				xf = (c as Node3D).transform * xf
			c = c.get_parent()
		for s in mi.mesh.get_surface_count():
			var arr := mi.mesh.surface_get_arrays(s)
			var v: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
			var t: PackedVector2Array = arr[Mesh.ARRAY_TEX_UV] if arr[Mesh.ARRAY_TEX_UV] != null else PackedVector2Array()
			var ix: PackedInt32Array = arr[Mesh.ARRAY_INDEX] if arr[Mesh.ARRAY_INDEX] != null else PackedInt32Array()
			if t.size() != v.size():
				continue
			var base := pos.size()
			for p in v:
				pos.append(xf * p)
			uv.append_array(t)
			if ix.is_empty():
				for k in v.size():
					idx.append(base + k)
			else:
				for k in ix:
					idx.append(base + k)
			if albedo == null:
				albedo = _albedo_image(mi.mesh.surface_get_material(s))
	root.free()
	var out := measure_mesh(pos, uv, idx, mask, albedo)
	out["texel"] = texel_share(mask)
	return out


static func _albedo_image(mat: Material) -> Image:
	var bm := mat as BaseMaterial3D
	if bm == null or bm.albedo_texture == null:
		return null
	var tex := bm.albedo_texture
	var img: Image = null
	if not tex.resource_path.is_empty() and FileAccess.file_exists(tex.resource_path):
		img = Image.load_from_file(ProjectSettings.globalize_path(tex.resource_path))
	if img == null:
		img = tex.get_image()
	if img != null and img.is_compressed():
		img.decompress()
	return img


## Share of mask texels >= 128 (0 without a mask).
static func texel_share(mask: Image) -> float:
	if mask == null:
		return 0.0
	var m := mask.duplicate() as Image
	m.convert(Image.FORMAT_L8)
	var d := m.get_data()
	var n := 0
	for b in d:
		if b >= 128:
			n += 1
	return float(n) / maxf(d.size(), 1.0)


## Team weight of one texel, as unit.gdshader (team_mode 2) computes it: `mask_v` 0..1, albedo in
## sRGB 0..1 (the shader samples it as linear).
static func team_weight(mask_v: float, r: float, g: float, b: float) -> float:
	var m := smoothstep(0.45, 0.8, mask_v)
	var lr := _lin(r)
	var lg := _lin(g)
	var lb := _lin(b)
	var key := smoothstep(0.18, 0.36, minf(lr, lb) - lg) * (1.0 if absf(lr - lb) <= 0.3 else 0.0)
	return maxf(m, key)


static func _lin(c: float) -> float:
	return c / 12.92 if c <= 0.04045 else pow((c + 0.055) / 1.055, 2.4)


## Rasterises triangles (`idx` into `pos` / `uv`, model space, +Y up) from the game camera at
## YAWS yaws. Returns {coverage, upper, silhouette_px}.
static func measure_mesh(pos: PackedVector3Array, uv: PackedVector2Array, idx: PackedInt32Array,
		mask: Image, albedo: Image) -> Dictionary:
	if pos.is_empty() or idx.size() < 3:
		return {"coverage": 0.0, "upper": 0.0, "silhouette_px": 0}
	var mk := _plane(mask, Image.FORMAT_L8)
	var al := _plane(albedo, Image.FORMAT_RGB8)
	var aabb := AABB(pos[0], Vector3.ZERO)
	for p in pos:
		aabb = aabb.expand(p)
	var centre := aabb.get_center()
	var radius := aabb.size.length() * 0.5
	var scale := RES * 0.48 / maxf(radius, 0.001)
	var upper_y := aabb.position.y + aabb.size.y * 2.0 / 3.0
	var sil := 0
	var team := 0.0
	var upper := 0.0
	var pitch := deg_to_rad(-PITCH_DEG)
	var f0 := Vector3(0.0, -sin(pitch), -cos(pitch))
	var u0 := Vector3(0.0, cos(pitch), -sin(pitch))
	for v in YAWS:
		var yaw := TAU * v / YAWS
		var rot := Basis(Vector3.UP, yaw)
		var r := rot * Vector3.RIGHT
		var f := rot * f0
		var u := rot * u0
		var res := _raster(pos, uv, idx, centre, r, u, f, scale, upper_y, mk, al)
		sil += int(res.x)
		team += res.y
		upper += res.z
	return {"coverage": team / maxf(sil, 1.0), "upper": upper / maxf(sil, 1.0), "silhouette_px": sil}


## [data, width, height, channels] of an image converted to `fmt` ([] without an image).
static func _plane(img: Image, fmt: Image.Format) -> Array:
	if img == null:
		return []
	var c := img.duplicate() as Image
	if c.is_compressed():
		c.decompress()
	c.convert(fmt)
	return [c.get_data(), c.get_width(), c.get_height(), 1 if fmt == Image.FORMAT_L8 else 3]


static func _sample_weight(t: Vector2, mk: Array, al: Array) -> float:
	var mv := 0.0
	if not mk.is_empty():
		var w: int = mk[1]
		var h: int = mk[2]
		var x := clampi(int(fposmod(t.x, 1.0) * w), 0, w - 1)
		var y := clampi(int(fposmod(t.y, 1.0) * h), 0, h - 1)
		mv = (mk[0] as PackedByteArray)[y * w + x] / 255.0
	var rr := 0.5
	var gg := 0.5
	var bb := 0.5
	if not al.is_empty():
		var w: int = al[1]
		var h: int = al[2]
		var x := clampi(int(fposmod(t.x, 1.0) * w), 0, w - 1)
		var y := clampi(int(fposmod(t.y, 1.0) * h), 0, h - 1)
		var o := (y * w + x) * 3
		var d: PackedByteArray = al[0]
		rr = d[o] / 255.0
		gg = d[o + 1] / 255.0
		bb = d[o + 2] / 255.0
	return team_weight(mv, rr, gg, bb)


## One view: returns Vector3(silhouette pixels, team weight sum, upper-third team weight sum).
static func _raster(pos: PackedVector3Array, uv: PackedVector2Array, idx: PackedInt32Array,
		centre: Vector3, r: Vector3, u: Vector3, f: Vector3, scale: float, upper_y: float,
		mk: Array, al: Array) -> Vector3:
	var n := pos.size()
	var sx := PackedFloat32Array()
	var sy := PackedFloat32Array()
	var sz := PackedFloat32Array()
	sx.resize(n)
	sy.resize(n)
	sz.resize(n)
	var half := RES * 0.5
	for i in n:
		var p := pos[i] - centre
		sx[i] = p.dot(r) * scale + half
		sy[i] = half - p.dot(u) * scale
		sz[i] = p.dot(f)
	var zbuf := PackedFloat32Array()
	zbuf.resize(RES * RES)
	zbuf.fill(INF)
	var wbuf := PackedFloat32Array()
	wbuf.resize(RES * RES)
	var hbuf := PackedByteArray()
	hbuf.resize(RES * RES)
	for k in range(0, idx.size() - 2, 3):
		var a := idx[k]
		var b := idx[k + 1]
		var c := idx[k + 2]
		var ax := sx[a]
		var ay := sy[a]
		var bx := sx[b]
		var by := sy[b]
		var cx := sx[c]
		var cy := sy[c]
		var area := (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
		if absf(area) < 1e-6:
			continue
		var x0 := maxi(int(floor(minf(ax, minf(bx, cx)))), 0)
		var x1 := mini(int(ceil(maxf(ax, maxf(bx, cx)))), RES - 1)
		var y0 := maxi(int(floor(minf(ay, minf(by, cy)))), 0)
		var y1 := mini(int(ceil(maxf(ay, maxf(by, cy)))), RES - 1)
		var inv := 1.0 / area
		for y in range(y0, y1 + 1):
			var py := y + 0.5
			for x in range(x0, x1 + 1):
				var px := x + 0.5
				var w0 := ((bx - px) * (cy - py) - (by - py) * (cx - px)) * inv
				var w1 := ((cx - px) * (ay - py) - (cy - py) * (ax - px)) * inv
				var w2 := 1.0 - w0 - w1
				if w0 < 0.0 or w1 < 0.0 or w2 < 0.0:
					continue
				var z := w0 * sz[a] + w1 * sz[b] + w2 * sz[c]
				var o := y * RES + x
				if z >= zbuf[o]:
					continue
				zbuf[o] = z
				var t := uv[a] * w0 + uv[b] * w1 + uv[c] * w2
				wbuf[o] = _sample_weight(t, mk, al)
				var hy := pos[a].y * w0 + pos[b].y * w1 + pos[c].y * w2
				hbuf[o] = 1 if hy >= upper_y else 0
	var sil := 0
	var team := 0.0
	var upper := 0.0
	if debug_image != null:
		debug_image.copy_from(Image.create(RES, RES, false, Image.FORMAT_RGB8))
	for o in RES * RES:
		if zbuf[o] == INF:
			continue
		sil += 1
		team += wbuf[o]
		if hbuf[o] == 1:
			upper += wbuf[o]
		if debug_image != null:
			var g := 0.45 + 0.15 * hbuf[o]
			debug_image.set_pixel(o % RES, o / RES, Color(g, g, g).lerp(Color(0.1, 0.9, 0.2), wbuf[o]))
	return Vector3(sil, team, upper)
