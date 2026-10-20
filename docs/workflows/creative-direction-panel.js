export const meta = {
  name: 'creative-direction-panel',
  description: 'Generate 4 original WC3-feel RTS world/faction concepts from different angles, judge with 3 lenses, return scored results',
  phases: [
    { title: 'Concepts', detail: '4 independent concept pitches' },
    { title: 'Judge', detail: '3 judges x 4 concepts' },
  ],
}

const BRIEF = `
You are a senior game designer + art director pitching the creative concept for "Vibecraft": an ORIGINAL 3D real-time strategy game in Godot 4.7 that should FEEL like Warcraft III (2002): heroic, chunky/exaggerated stylized fantasy, saturated hand-painted look, heroes with levels and abilities, creep camps, items, gold + lumber style economy with upkeep, small armies (~20-40 units), funny/charming unit voice responses, epic music, top-down 3/4 perspective camera. The user (a WC3 fan) explicitly wants creativity and does NOT want the generic Freecraft(1999)/Stratagus feel (generic medieval humans vs generic orcs with flat sprite look). It must avoid copyright/trademark issues: no Warcraft names, characters, races-as-depicted, unit names, spell names, voice lines, UI art. Generic fantasy concepts are fine but our factions must be clearly ORIGINAL.

PRODUCTION CONSTRAINTS (very important for scoring):
- Assets are AI-generated: concept images (cheap), image-to-3D models (~25-30 models total budget for the vertical slice), auto-rigging works best on HUMANOID bipeds (non-bipeds rig poorly; can be animated procedurally if simple, e.g., hovering/rolling/floating/wheeled constructs, slithering is hard). Buildings are static meshes (can be procedurally animated: bobbing, rotating parts, glows). Terrain textures and icons are cheap images. Sound effects and voice lines via text-to-audio/TTS are cheap; music via AI music model.
- Vertical slice: 1 map, 2 playable factions (player vs AI), each with: 1 worker, 3-4 combat units, 1-2 heroes, 5-6 buildings; plus 2-3 neutral creep types and props (trees, rocks, gold-equivalent mine). Design must be READABLE from a top-down camera at small scale (strong silhouettes, team color areas).
`

const ANGLES = [
  { key: 'resonance', angle: 'ANGLE "Resonance": lean into the name VIBECRAFT - a world where magic, industry and war run on sound, vibration, rhythm, and resonance (bells, drums, horns, tuning crystals, choirs, echoes). Make it feel heroic and fun, not gimmicky; the audio identity should be the core of the fantasy.' },
  { key: 'folklore', angle: 'ANGLE "Folklore": take an UNDER-USED real-world mythology/folklore tradition (e.g., Slavic/Carpathian, Baltic, Finnish/Karelian, Mesoamerican, Polynesian, West African, Mongolian steppe...) and give it WC3-style heroic exaggeration. Pick the one that gives the most visually distinct, readable factions. Avoid looking like an existing game (e.g., Gord, The Witcher).' },
  { key: 'fidelity', angle: 'ANGLE "Nostalgic fidelity": maximize the WC3 nostalgia hit (stalwart civilization vs. savage horde vs. nature spirits vs. undead-like plague archetypes) BUT give each archetype a fresh, specific, original twist so nobody could mistake it for a Blizzard race. Keep the comfortable familiarity of WC3 gameplay roles.' },
  { key: 'wildcard', angle: 'ANGLE "Wildcard": the most surprising and memorable concept that still plays exactly like WC3 (heroes, creeps, gold+lumber analog, bases). Think of an unexpected setting/scale or premise (e.g., living giant creatures as terrain, fungal kingdoms vs clockwork, a world inside a storm, tidal/moon-driven). Must still produce readable, chunky, charming units.' },
]

const CONCEPT = {
  type: 'object',
  properties: {
    title: { type: 'string' },
    logline: { type: 'string' },
    world: { type: 'string', description: '1-2 paragraphs: setting, conflict, tone' },
    why_not_generic: { type: 'string' },
    factions: { type: 'array', items: { type: 'object', properties: {
      name: { type: 'string' }, fantasy: { type: 'string' }, unique_mechanic: { type: 'string' },
      visual_identity: { type: 'string', description: 'silhouette language, materials, palette (hex), team color placement' },
      audio_identity: { type: 'string', description: 'voice personality, sample unit responses (original), music instrumentation' },
      worker: { type: 'string' },
      units: { type: 'array', items: { type: 'string' }, description: '3-4 combat units: name - role - look - 1 ability' },
      heroes: { type: 'array', items: { type: 'string' }, description: '2 heroes: name/title - role - 4 abilities (last is ultimate)' },
      buildings: { type: 'array', items: { type: 'string' }, description: '5-6 buildings: name - function - look' },
    }, required: ['name','fantasy','unique_mechanic','visual_identity','audio_identity','worker','units','heroes','buildings'] }, description: 'exactly 2 vertical-slice factions' },
    later_factions: { type: 'array', items: { type: 'string' }, description: '2 more factions for later, one line each' },
    resources: { type: 'string', description: 'gold/lumber analogs + food/upkeep flavor' },
    creeps: { type: 'array', items: { type: 'string' } },
    tileset: { type: 'string', description: 'the vertical slice map biome, terrain textures, doodads, day/night mood' },
    art_direction: { type: 'string', description: 'concrete style guide for AI image prompts: shape language, palette, lighting, materials, what to avoid' },
    music_direction: { type: 'string' },
    producibility_notes: { type: 'string', description: 'how this fits the AI pipeline (bipeds for rigging, etc.) and risks' },
  },
  required: ['title','logline','world','why_not_generic','factions','later_factions','resources','creeps','tileset','art_direction','music_direction','producibility_notes'],
}

const SCORE = {
  type: 'object',
  properties: {
    scores: { type: 'array', items: { type: 'object', properties: {
      concept: { type: 'string' },
      wc3_feel: { type: 'number' }, originality: { type: 'number' }, ip_safety: { type: 'number' },
      producibility: { type: 'number' }, readability_gameplay: { type: 'number' },
      best_ideas_to_keep: { type: 'array', items: { type: 'string' } },
      weaknesses: { type: 'array', items: { type: 'string' } },
    }, required: ['concept','wc3_feel','originality','ip_safety','producibility','readability_gameplay','best_ideas_to_keep','weaknesses'] } },
    winner: { type: 'string' },
    rationale: { type: 'string' },
  },
  required: ['scores','winner','rationale'],
}

phase('Concepts')
const concepts = (await parallel(ANGLES.map(a => () =>
  agent(`${BRIEF}\n\n${a.angle}\n\nYou may use WebSearch briefly to check that your faction/unit names are not existing well-known game IP. Produce one complete concept.`, { label: `concept:${a.key}`, phase: 'Concepts', schema: CONCEPT })
    .then(c => c ? { key: a.key, ...c } : null)
))).filter(Boolean)

phase('Judge')
const packet = JSON.stringify(concepts.map(c => ({ key: c.key, ...c })), null, 1)
const LENSES = [
  { key: 'wc3fan', lens: 'You are a lifelong Warcraft III fan and competitive player. Judge which concept would most make a WC3 fan feel at home AND excited, while still feeling new. Weight wc3_feel and readability_gameplay highest.' },
  { key: 'artdirector', lens: 'You are an art director + IP-cautious producer. Judge originality, visual distinctiveness top-down, IP safety, and how cohesive the art can be with AI-generated assets. Weight originality and ip_safety highest.' },
  { key: 'producer', lens: 'You are a technical producer for a tiny team using AI-generated assets (image-to-3D ~25-30 models, humanoid auto-rigging only, cheap images/audio). Judge producibility and scope risk for a playable vertical slice. Weight producibility highest.' },
]
const judgements = (await parallel(LENSES.map(l => () =>
  agent(`${BRIEF}\n\n${l.lens}\n\nScore EACH concept 1-10 on every criterion and pick a winner. Concepts:\n${packet}`, { label: `judge:${l.key}`, phase: 'Judge', schema: SCORE })
    .then(j => j ? { lens: l.key, ...j } : null)
))).filter(Boolean)

return { concepts, judgements }
