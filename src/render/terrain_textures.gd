class_name TerrainTextures
extends RefCounted
## Greenvale terrain textures (art bible §6): the 7-tile ladder as one Texture2DArray in draw
## order (0 scree .. 6 thick meadow), plus mipmapped cliff / water / bark textures. The source PNGs
## are imported lossless without mipmaps, so mip chains are generated here once and cached.
## Missing files fall back to a flat colour slice (the "runs without art" rule).

const LADDER: Array[String] = ["gv_scree", "gv_cracked", "gv_dirt", "gv_road", "gv_grassy_dirt",
	"gv_meadow", "gv_thick_meadow"]
## Ladder slots by name (draw order: a later slot overlaps an earlier one at a shared corner).
const SCREE := 0
const CRACKED := 1
const DIRT := 2
const ROAD := 3
const GRASSY_DIRT := 4
const MEADOW := 5
const THICK_MEADOW := 6
## Art bible §6.1 base colours, used when a texture file is missing.
const FALLBACK: Array[Color] = [Color("#7D766A"), Color("#A88C60"), Color("#8C6F4D"),
	Color("#A08560"), Color("#7E7A45"), Color("#799A55"), Color("#5B7A43")]
const DIR := "res://assets/textures/terrain/"
const SIZE := 1024

static var _array: Texture2DArray
static var _single: Dictionary = {}


static func ladder_array() -> Texture2DArray:
	if _array != null:
		return _array
	var images: Array[Image] = []
	for i in LADDER.size():
		images.append(_image(DIR + LADDER[i] + ".png", FALLBACK[i]))
	_array = Texture2DArray.new()
	_array.create_from_images(images)
	return _array


## Mipmapped copy of a texture file (cliff, water ripples, bark), cached.
static func mipmapped(file_name: String, fallback: Color = Color(0.5, 0.5, 0.5)) -> Texture2D:
	if _single.has(file_name):
		return _single[file_name]
	var img := _image(DIR + file_name, fallback)
	var tex := ImageTexture.create_from_image(img)
	_single[file_name] = tex
	return tex


static func _image(path: String, fallback: Color) -> Image:
	var img: Image = null
	if ResourceLoader.exists(path):
		var t := load(path) as Texture2D
		if t != null:
			img = t.get_image()
	if img == null or img.is_empty():
		img = Image.create(64, 64, false, Image.FORMAT_RGB8)
		img.fill(fallback)
	if img.is_compressed():
		img.decompress()
	if img.get_format() != Image.FORMAT_RGB8:
		img.convert(Image.FORMAT_RGB8)
	if img.get_width() != SIZE or img.get_height() != SIZE:
		img.resize(SIZE, SIZE, Image.INTERPOLATE_BILINEAR)
	if not img.has_mipmaps():
		img.generate_mipmaps()
	return img


static func clear_cache() -> void:
	_array = null
	_single.clear()
