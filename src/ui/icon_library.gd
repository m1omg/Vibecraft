class_name IconLibrary
extends RefCounted
## The 128 px game icons (art bible §5.5 T9) by def id: items (assets/ui/icons/items), buildings
## (assets/ui/icons/buildings, rendered from the game's own models) and shop services
## (assets/ui/icons/services); built by tools/assets/icon_sheets.py. Visual only. Ids without an
## icon (units, commands, research for now) return null and keep their coloured face and label.
## Disabled and locked faces use the greyscale copy (bible §7.4: greyscale × 0.55), made once per
## icon on first use.

const DIRS: Array[String] = ["res://assets/ui/icons/items/", "res://assets/ui/icons/buildings/",
	"res://assets/ui/icons/services/"]
## Services that borrow another icon.
const ALIASES := {"neutral_inn_revive": "neutral_coaching_inn"}
const GREY_VALUE := 0.55

static var _cache: Dictionary = {}       ## id -> Texture2D or null
static var _grey: Dictionary = {}        ## id -> Texture2D


static func has(id: String) -> bool:
	return texture(id) != null


## The icon for `id`, or null.
static func texture(id: String) -> Texture2D:
	if id.is_empty():
		return null
	if _cache.has(id):
		return _cache[id]
	var key: String = ALIASES.get(id, id)
	var tex: Texture2D = null
	for d in DIRS:
		var p := d + key + ".png"
		if ResourceLoader.exists(p):
			tex = load(p) as Texture2D
			break
	_cache[id] = tex
	return tex


## The greyscale, darkened copy for disabled and locked faces (null when `id` has no icon).
static func grey(id: String) -> Texture2D:
	if _grey.has(id):
		return _grey[id]
	var tex := texture(id)
	if tex == null:
		return null
	var img := tex.get_image()
	if img == null:
		return tex
	img = img.duplicate() as Image
	if img.is_compressed():
		img.decompress()
	img.clear_mipmaps()
	img.adjust_bcs(GREY_VALUE, 1.0, 0.0)
	img.generate_mipmaps()
	var out := ImageTexture.create_from_image(img)
	_grey[id] = out
	return out
