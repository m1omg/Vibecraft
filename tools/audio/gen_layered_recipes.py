#!/usr/bin/env python3
"""Writes tools/audio/layered_recipes.json (CC0 and procedural placeholder takes). Edit here, run, then run build_layered_sfx.py."""
import json
IS='kenney/impact-sounds/'; RP='kenney/rpg-audio/'
R=[]
def rec(id,group,source,takes,note=""):
    R.append({"id":id,"group":group,"source":source,"note":note,"takes":takes})
# body falls (CC0, bible 11 decision 2b)
rec("fall_light","combat","cc0",[{"layers":[
    {"src":IS+"impactSoft_heavy_00%d.ogg"%a,"pitch":p},
    {"src":IS+"impactPunch_medium_00%d.ogg"%b,"gain_db":-4,"lp":2200,"pitch":0.85,"offset_ms":5},
    {"src":RP+"cloth%d.ogg"%c,"gain_db":-8,"hp":400,"offset_ms":12}]}
    for a,b,c,p in ((0,0,1,1.0),(1,1,3,0.94),(2,4,2,1.06))],"Kenney Impact Sounds + RPG Audio (CC0), layered")
rec("fall_armoured","combat","cc0",[{"layers":[
    {"src":IS+"impactSoft_heavy_00%d.ogg"%a,"pitch":0.9},
    {"src":IS+"impactPunch_heavy_00%d.ogg"%a,"pitch":0.85,"lp":2500,"gain_db":-4},
    {"src":IS+"impactPlate_medium_00%d.ogg"%b,"gain_db":-5,"offset_ms":25},
    {"src":IS+"impactPlate_light_00%d.ogg"%c,"gain_db":-11,"offset_ms":150},
    {"src":IS+"impactMetal_light_00%d.ogg"%d,"gain_db":-13,"pitch":0.8,"offset_ms":60}]}
    for a,b,c,d in ((3,0,1,0),(4,2,3,2),(0,4,4,4))],"Kenney Impact Sounds (CC0), layered")
rec("fall_huge","combat","cc0",[{"layers":[
    {"src":IS+"impactSoft_heavy_00%d.ogg"%a,"pitch":0.7,"gain_db":-2},
    {"src":IS+"impactPunch_heavy_00%d.ogg"%a,"pitch":0.65,"lp":2000,"gain_db":0},
    {"src":IS+"impactWood_heavy_00%d.ogg"%b,"pitch":0.6,"gain_db":-8},
    {"src":IS+"impactPlank_medium_00%d.ogg"%c,"pitch":0.75,"gain_db":-7,"lp":1800,"offset_ms":30},
    {"synth":"rumble","dur":1.0,"lp":160,"decay":0.35,"gain_db":-8}]}
    for a,b,c in ((1,0,1),(2,2,2),(3,4,3))],"Kenney Impact Sounds (CC0) + procedural rumble")
# procedural sub-thump (CMB-27 hit_sub)
rec("hit_sub","combat","procedural",[{"lp":160,"layers":[{"synth":"thump","f0":f0,"f1":f1,"decay":d,"dur":0.3}]}
    for f0,f1,d in ((62,36,0.10),(58,34,0.12),(66,38,0.09),(54,32,0.13))],"procedural sine thump")
# UI (bible 11 decision 2b: UI clicks and ticks may be CC0): placeholders until the 9.2 kit sets are generated
rec("ui_click_kingdom","ui","cc0",[{"layers":[
    {"src":IS+"impactWood_light_00%d.ogg"%a,"pitch":p,"len_ms":120},
    {"synth":"tick","f":f,"decay":0.003,"gain_db":-11,"hp":2500,"offset_ms":4}]}
    for a,p,f in ((0,1.3,4200),(1,1.25,4500),(2,1.35,4000),(3,1.3,4700),(4,1.4,4300),(1,1.2,3900))],"oak knock (Kenney CC0) + procedural latch tick")
rec("ui_click_clans","ui","cc0",[{"layers":[
    {"src":IS+"impactSoft_medium_00%d.ogg"%a,"pitch":1.6,"len_ms":120},
    {"src":IS+"impactPunch_medium_00%d.ogg"%a,"pitch":1.3,"lp":1800,"len_ms":120,"gain_db":-5},
    {"src":IS+"impactMetal_light_00%d.ogg"%b,"pitch":p,"len_ms":60,"hp":1500,"gain_db":-12,"fade_ms":30}]}
    for a,b,p in ((0,0,1.3),(1,1,1.35),(2,2,1.25),(3,3,1.3),(4,4,1.4),(2,1,1.2))],"felt thump + damped bronze tick (Kenney CC0)")
rec("ui_disabled_kingdom","ui","cc0",[{"layers":[{"src":IS+"impactWood_medium_00%d.ogg"%a,"pitch":p,"lp":900,"len_ms":220}]}
    for a,p in ((0,0.9),(2,0.88),(4,0.92))],"muffled board knock (Kenney CC0)")
rec("ui_disabled_clans","ui","cc0",[{"layers":[{"src":IS+"impactSoft_medium_00%d.ogg"%a,"pitch":p,"lp":700},{"src":IS+"impactPunch_medium_00%d.ogg"%a,"pitch":0.9,"lp":900,"gain_db":-6}]}
    for a,p in ((1,1.0),(3,0.95),(4,1.05))],"felt thud (Kenney CC0)")
rec("ui_error_kingdom","ui","cc0",[{"layers":[
    {"src":IS+"impactWood_medium_00%d.ogg"%a,"pitch":p,"lp":1200},
    {"src":IS+"impactWood_medium_00%d.ogg"%b,"pitch":p*0.97,"lp":1100,"offset_ms":gap,"gain_db":-2}]}
    for a,b,p,gap in ((0,1,0.8,120),(2,3,0.78,115),(4,0,0.82,125),(1,4,0.79,118))],"dull double knock (Kenney CC0)")
rec("ui_error_clans","ui","cc0",[{"layers":[
    {"src":IS+"impactSoft_heavy_00%d.ogg"%a,"pitch":1.2,"len_ms":220,"lp":800},
    {"src":IS+"impactPunch_medium_00%d.ogg"%a,"pitch":0.9,"lp":1000,"len_ms":220,"gain_db":-6},
    {"synth":"bowl","f0":f0,"decay":0.6,"choke_ms":210,"dur":0.35,"gain_db":-7,"lp":1600,"offset_ms":40}]}
    for a,f0 in ((0,110),(1,117),(2,104),(3,123))],"felt thud (Kenney CC0) + procedural choked bronze bowl tone")
# order ticks
def wood(i,p,off=0,g=0,ln=100): return {"src":IS+"impactWood_light_00%d.ogg"%i,"pitch":p,"offset_ms":off,"gain_db":g,"len_ms":ln}
def felt(i,p,off=0,g=0,ln=100): return [{"src":IS+"impactSoft_medium_00%d.ogg"%i,"pitch":p,"offset_ms":off,"gain_db":g,"len_ms":ln},{"src":IS+"impactPunch_medium_00%d.ogg"%i,"pitch":1.3,"lp":1800,"offset_ms":off,"gain_db":g-5,"len_ms":ln}]
def tsk(off=0,g=-6): return {"synth":"noise","dur":0.04,"hp":3500,"decay":0.012,"gain_db":g,"offset_ms":off}
def tick(f,off=0,g=-9): return {"synth":"tick","f":f,"decay":0.003,"hp":2500,"gain_db":g,"offset_ms":off}
ok=[]
for v,(a,b,p) in enumerate(((0,1,1.5),(2,3,1.6))):
    ok.append(("move",[wood(a,p)]))
for v,(a,p) in enumerate(((1,1.6),(3,1.7))):
    ok.append(("attack",[tsk(),wood(a,p,45),tick(3800+300*v,45)]))
for v,(a,b,p) in enumerate(((0,2,1.5),(1,4,1.55))):
    ok.append(("patrol",[wood(a,p),wood(b,p*1.06,85,-1)]))
for v,f in enumerate(("bookFlip3.ogg","bookFlip2.ogg")):
    ok.append(("ability",[{"src":RP+f,"len_ms":160,"hp":1500,"pitch":1.15+0.1*v}]))
for name,layers in ok:
    pass
def kit(id,items,note):
    takes=[]; names=[]
    for name,layers in items:
        takes.append({"name":name,"layers":layers})
    rec(id,"ui","cc0",takes,note)
kit("ui_order_kingdom",ok,"order ticks: wood tuk, tsk-tak with iron click, tuk-tuk, page flick (Kenney CC0 + procedural)")
oc=[]
for a,p in ((0,1.8),(2,1.9)): oc.append(("move",felt(a,p)))
for v,(a,b) in enumerate(((1,1),(3,3))):
    oc.append(("attack",[tsk()]+felt(a,1.8,45)+[{"src":IS+"impactMetal_light_00%d.ogg"%b,"pitch":1.5,"len_ms":50,"hp":1500,"gain_db":-9,"offset_ms":45,"fade_ms":25}]))
for a,b in ((0,2),(1,4)): oc.append(("patrol",felt(a,1.8)+felt(b,1.9,85,-1)))
for v in range(2):
    oc.append(("ability",[wood((v+i)%5,2.4+0.1*i,[0,35,62,85][i],-3*i,60) for i in range(4)]))
kit("ui_order_clans",oc,"order ticks: felt puk, tsk-tak with bronze click, puk-puk, bead run (Kenney CC0 + procedural)")
sk=[]
for v,(a,p) in enumerate(((0,1.9),(2,2.0))): sk.append(("single",[wood(a,p,0,0,70)]))
for v,(a,b,p) in enumerate(((1,3,1.9),(4,0,2.0))): sk.append(("double",[wood(a,p,0,0,70),wood(b,p*1.04,70,-1,70)]))
import random
rnd=random.Random(7)
for v in range(2):
    sk.append(("bundle",[wood(rnd.randrange(5),rnd.uniform(1.5,2.2),int(rnd.uniform(0,120)) if i else 0,-rnd.uniform(0,6),80) for i in range(5)]))
for v,(a,p) in enumerate(((0,2.3),(3,2.4))): sk.append(("wave",[wood(a,p,0,0,70)]))
kit("ui_select_kingdom",sk,"tally-stick ticks: single, double, bundle clack, higher wave tick (Kenney CC0)")
sc=[]
for v,(a,p) in enumerate(((0,2.7),(2,2.8))): sc.append(("single",[wood(a,p,0,0,50),tick(5200,0,-14)]))
for v,(a,b,p) in enumerate(((1,3,2.7),(4,0,2.8))): sc.append(("double",[wood(a,p,0,0,50),wood(b,p*1.04,60,-1,50)]))
for v in range(2):
    sc.append(("bundle",[wood(rnd.randrange(5),rnd.uniform(2.5,3.1),int(i*28+rnd.uniform(0,10)),-rnd.uniform(0,7),50) for i in range(7)]))
for v,(a,p) in enumerate(((0,3.2),(3,3.3))): sc.append(("wave",[wood(a,p,0,0,50)]))
kit("ui_select_clans",sc,"wooden bead ticks: single, double, bead-string rattle, higher wave tick (Kenney CC0)")
# derived from our own generated takes (Seed Audio) plus CC0 layers: material variants and heavier versions
def own(f,**k): d={"own":f}; d.update(k); return d
def dirt(off=0,g=-8): return {"synth":"noise","dur":0.25,"lp":3500,"hp":200,"decay":0.06,"attack":0.004,"gain_db":g,"offset_ms":off}
rec("bullet_hit","ranged","derived",[
    {"name":"flesh","max_ms":300,"layers":[own("combat/hit_flesh_l_02.wav",pitch=1.25)]},
    {"name":"wood","max_ms":300,"layers":[own("combat/hit_wood_l_03.wav",pitch=1.3)]},
    {"name":"metal","max_ms":300,"layers":[own("combat/hit_metal_l_01.wav",pitch=1.5),tick(5200,0,-6)]},
    {"name":"earth","max_ms":300,"layers":[{"src":IS+"impactSoft_medium_002.ogg","pitch":1.4},dirt(0,-4)]}],
    "lead-ball hits by material, derived from our hit_* takes (Seed Audio) and Kenney CC0")
rec("javelin_hit","ranged","derived",[
    {"name":"wood","max_ms":450,"layers":[own("combat/hit_wood_l_01.wav",pitch=0.95),{"src":IS+"impactWood_medium_001.ogg","gain_db":-6}]},
    {"name":"flesh","max_ms":450,"layers":[own("combat/hit_flesh_l_03.wav",pitch=0.9)]},
    {"name":"metal","max_ms":450,"layers":[own("combat/hit_metal_l_02.wav",pitch=1.1),own("combat/hit_wood_l_02.wav",pitch=1.2,gain_db=-10)]},
    {"name":"earth","max_ms":450,"layers":[{"src":IS+"impactSoft_heavy_001.ogg","pitch":1.1},{"src":IS+"impactPunch_medium_002.ogg","lp":1500,"gain_db":-6},dirt(5,-6)]}],
    "javelin hits by material, derived from our hit_* takes (Seed Audio) and Kenney CC0")
rec("hit_wood_h","combat","derived",[{"max_ms":650,"fade_out_ms":80,"layers":[
    own("combat/hit_wood_l_%02d.wav"%a,pitch=p),
    {"src":IS+"impactPlank_medium_00%d.ogg"%b,"gain_db":-3,"offset_ms":5},
    {"src":IS+"impactWood_heavy_00%d.ogg"%c,"pitch":0.9,"gain_db":-5}]}
    for a,b,c,p in ((1,0,0,0.8),(2,3,2,0.78),(3,4,4,0.82),(1,2,1,0.75))],
    "heavy blow on planks: our hit_wood_l (Seed Audio) pitched down + Kenney CC0 plank crack")
rec("claypot_hit","ranged","derived",[{"max_ms":800,"fade_out_ms":150,"layers":[
    own("ranged/bombard_hit_%02d.wav"%a,pitch=1.5,gain_db=-2),
    {"src":IS+"impactGlass_heavy_00%d.ogg"%b,"pitch":0.7,"lp":5000,"gain_db":-7},
    {"src":IS+"impactSoft_heavy_00%d.ogg"%c,"pitch":1.1,"gain_db":-3},
    {"synth":"noise","dur":0.6,"lp":2500,"hp":150,"decay":0.15,"attack":0.01,"gain_db":-11,"offset_ms":20}]}
    for a,b,c in ((1,0,0),(3,2,2),(4,4,3),(5,1,4))],
    "clay pot smash: our bombard_hit debris (Seed Audio) pitched up + Kenney CC0 crack and thump + procedural dust")
rec("sw_pierce","combat","derived",[{"max_ms":260,"fade_out_ms":70,"layers":[own("combat/sw_slash_%02d.wav"%a,pitch=p,start_ms=st)]}
    for a,p,st in ((1,1.25,60),(3,1.3,50),(4,1.2,70),(1,1.35,40))],
    "placeholder: short sharp air cuts derived from our sw_slash takes (Seed Audio), pitched up and shortened")
rec("vox_death_clans","combat","derived",[{"layers":[own("combat/vox_death_kingdom_%02d.wav"%a,pitch=p)]}
    for a,p in ((1,0.72),(2,0.7),(3,0.74))],
    "placeholder until generated: our vox_death_kingdom takes (Seed Audio) pitched down to a deep-chested register")
# economy and buildings (juice ECO-*/BLD-*, Playtest 2): CC0 impacts + procedural bowls, all ours to layer
def bowl(f0,dec,dur,off=0,g=0,lp=0): d={"synth":"bowl","f0":f0,"decay":dec,"dur":dur,"offset_ms":off,"gain_db":g}; d.update({"lp":lp} if lp else {}); return d
rec("bld_stamp","world","cc0",[{"layers":[
    {"src":IS+"impactSoft_heavy_00%d.ogg"%a,"pitch":0.75},
    {"src":IS+"impactPlank_medium_00%d.ogg"%b,"pitch":0.8,"gain_db":-6,"offset_ms":15},
    {"synth":"thump","f0":72,"f1":40,"decay":0.12,"dur":0.35,"gain_db":-6}]}
    for a,b in ((0,1),(2,3),(4,0))],"site stamp: foundation thump (Kenney CC0) + procedural sub thump")
rec("bld_hammer","world","cc0",[{"max_ms":260,"layers":[
    {"src":IS+"impactWood_light_00%d.ogg"%a,"pitch":p,"len_ms":160},
    {"src":IS+"impactPlank_medium_00%d.ogg"%b,"pitch":1.3,"len_ms":120,"hp":400,"gain_db":-12},
    tick(2800,0,-15)]}
    for a,b,p in ((0,0,1.0),(1,2,1.06),(2,4,0.96),(3,1,1.1),(4,3,1.02),(1,0,0.92))],"kingdom builder's hammer on timber (Kenney CC0 + procedural tick)")
rec("bld_mallet","world","cc0",[{"max_ms":260,"layers":[
    {"src":IS+"impactSoft_medium_00%d.ogg"%a,"pitch":1.2,"len_ms":160},
    {"src":IS+"impactWood_light_00%d.ogg"%b,"pitch":0.8,"lp":1500,"len_ms":140,"gain_db":-6}]}
    for a,b in ((0,1),(1,3),(2,0),(3,4))],"clans felt mallet on lattice (Kenney CC0)")
rec("bld_complete","world","procedural",[{"layers":[
    bowl(f0,1.2,1.6,0,0,6000), bowl(f0*1.5,0.9,1.3,90,-4,7000),
    {"src":IS+"impactWood_light_00%d.ogg"%a,"pitch":1.2,"gain_db":-9,"len_ms":120},
    tick(5000,90,-16)]}
    for f0,a in ((523.25,0),(493.88,2))],"topping-out chime: two procedural bronze bowls a fifth apart + a wood knock (Kenney CC0)")
rec("bld_tier_up","world","procedural",[{"layers":[
    bowl(f0,1.8,2.4,0,0,5000), bowl(f0*1.5,1.5,2.2,120,-3,6000), bowl(f0*2,1.2,2.0,240,-5,7000),
    {"synth":"rumble","dur":1.4,"lp":120,"decay":0.5,"attack":0.25,"gain_db":-12},
    {"src":IS+"impactPlate_medium_00%d.ogg"%a,"pitch":0.8,"gain_db":-9}]}
    for f0,a in ((261.63,0),(246.94,3))],"hall raised: three procedural bowls rising + a swell (procedural) + a plate ring (Kenney CC0)")
rec("bld_collapse","world","cc0",[{"max_ms":2600,"fade_out_ms":400,"layers":[
    {"src":IS+"impactPlank_medium_00%d.ogg"%a,"pitch":0.6},
    {"src":IS+"impactWood_heavy_00%d.ogg"%b,"pitch":0.55,"offset_ms":60},
    {"src":IS+"impactWood_heavy_00%d.ogg"%c,"pitch":0.7,"offset_ms":220,"gain_db":-4},
    {"src":IS+"impactSoft_heavy_00%d.ogg"%a,"pitch":0.6,"offset_ms":120,"gain_db":-2},
    {"synth":"rumble","dur":1.8,"lp":140,"decay":0.6,"gain_db":-4},
    {"synth":"noise","dur":1.4,"lp":2500,"hp":300,"decay":0.35,"attack":0.05,"gain_db":-13,"offset_ms":100}]}
    for a,b,c in ((0,1,3),(2,4,0))],"cave-in: planks and beams (Kenney CC0) over a procedural rumble and debris hiss")
rec("eco_chop","world","cc0",[{"max_ms":320,"layers":[
    {"src":IS+"impactWood_heavy_00%d.ogg"%a,"pitch":p,"len_ms":220,"lp":4000},
    {"src":IS+"impactPunch_medium_00%d.ogg"%b,"lp":1200,"gain_db":-8,"len_ms":160},
    {"synth":"noise","dur":0.06,"hp":2000,"decay":0.01,"gain_db":-12}]}
    for a,b,p in ((0,0,1.15),(1,2,1.2),(2,4,1.1),(3,1,1.25),(4,3,1.18))],"axe into green wood (Kenney CC0) + a procedural bark chip")
rec("eco_tree_fall","world","cc0",[{"max_ms":2200,"fade_out_ms":300,"layers":[
    {"src":IS+"impactPlank_medium_00%d.ogg"%a,"pitch":0.45,"reverse":True,"gain_db":-9,"lp":1800},
    {"synth":"noise","dur":0.6,"lp":1400,"hp":180,"decay":0.25,"reverse":True,"gain_db":-10,"offset_ms":260},
    {"src":IS+"impactWood_heavy_00%d.ogg"%b,"pitch":0.5,"offset_ms":820},
    {"src":IS+"impactSoft_heavy_00%d.ogg"%c,"pitch":0.55,"offset_ms":820,"gain_db":-2},
    {"synth":"rumble","dur":0.8,"lp":130,"decay":0.3,"gain_db":-10,"offset_ms":820}]}
    for a,b,c in ((1,0,2),(3,2,4))],"tree topple: a reversed plank groan and whoosh into a heavy thud (Kenney CC0 + procedural)")
rec("eco_coin","world","cc0",[{"max_ms":420,"layers":[
    {"src":IS+"impactMetal_light_00%d.ogg"%a,"pitch":p,"len_ms":240,"hp":1500,"fade_ms":60},
    {"src":IS+"impactMetal_light_00%d.ogg"%b,"pitch":p*1.17,"len_ms":220,"hp":2000,"gain_db":-4,"offset_ms":55,"fade_ms":60},
    tick(6000,0,-12)]}
    for a,b,p in ((0,1,1.8),(2,3,1.9),(4,0,1.75),(1,4,2.0),(3,2,1.85))],"coins into the hall: two small metal clinks (Kenney CC0, pitched up) + tick")
rec("eco_lumber_drop","world","cc0",[{"max_ms":520,"layers":[
    {"src":IS+"impactPlank_medium_00%d.ogg"%a,"pitch":1.0,"len_ms":300},
    {"src":IS+"impactWood_light_00%d.ogg"%b,"pitch":0.9,"offset_ms":70,"gain_db":-6,"len_ms":140},
    {"src":IS+"impactWood_light_00%d.ogg"%c,"pitch":1.1,"offset_ms":130,"gain_db":-9,"len_ms":140}]}
    for a,b,c in ((0,1,2),(2,3,4),(4,0,1))],"logs onto the pile (Kenney CC0)")
rec("ui_research_done","ui","procedural",[{"layers":[
    bowl(659.25,0.9,1.2,0,-2,7000), bowl(987.77,0.7,1.0,110,-6,8000), tick(4200,0,-14)]}
    for _ in range(1)],"research done: two procedural bowls a fifth apart")
# heroes (juice HER-03/04/06/07, Playtest 3): procedural bowls and bells on D, CC0 knocks
LADDER=(587.33,659.26,739.99,880.0,987.77,1174.66,1318.51,1479.98,1760.0)   # D major pentatonic, levels 2..10
rec("hero_xp_kingdom","heroes","cc0",[{"max_ms":160,"layers":[
    {"src":IS+"impactWood_light_00%d.ogg"%a,"pitch":p,"len_ms":80,"hp":900},
    tick(f,0,-8)]}
    for a,p,f in ((0,1.7,4200),(2,1.8,4500),(4,1.65,4000))],"XP spoke-chip clicks into the wheel: an ivory knock (Kenney CC0, pitched up) + procedural tick")
rec("hero_xp_clans","heroes","procedural",[{"layers":[
    bowl(f0,0.22,0.45,0,0,9000), tick(6000,0,-14)]}
    for f0 in (2637.0,2793.8,2489.0)],"XP fleck tings the gong: a small procedural bronze bowl")
rec("hero_level_kingdom","heroes","procedural",[{"layers":[
    {"src":IS+"impactMetal_light_00%d.ogg"%a,"pitch":0.7,"len_ms":160,"gain_db":-6},
    {"src":IS+"impactPlate_light_00%d.ogg"%b,"pitch":0.9,"len_ms":200,"gain_db":-10,"offset_ms":40},
    bowl(293.66,1.4,1.6,0,-3,6000), bowl(369.99,1.2,1.5,90,-5,7000), bowl(440.0,1.1,1.4,180,-6,7000),
    bowl(587.33,1.3,1.4,300,-4,8000)]}
    for a,b in ((0,1),(2,3))],"kingdom level-up: a ratchet clack (Kenney CC0) and a rising arpeggio of procedural bells on D")
rec("hero_level_clans","heroes","procedural",[{"layers":[
    bowl(146.83,2.2,1.6,0,0,3000), {"synth":"rumble","dur":1.2,"lp":110,"decay":0.5,"attack":0.04,"gain_db":-14},
    bowl(293.66,1.4,1.5,120,-5,6000), bowl(440.0,1.1,1.4,240,-7,7000)]}
    for _ in range(2)],"Tormai level-up: a struck procedural gong on D under two bronze bowls")
rec("hero_bell_kingdom","heroes","procedural",[{"name":"l%d"%(i+2),"layers":[
    bowl(f0,1.0,1.4,0,0,9000), tick(5200,0,-16)]}
    for i,f0 in enumerate(LADDER)],"the level's ladder bell (kingdom): one step up a D pentatonic ladder per level")
rec("hero_bell_clans","heroes","procedural",[{"name":"l%d"%(i+2),"layers":[
    bowl(f0,1.6,1.8,0,0,5000), bowl(f0*1.5,1.0,1.4,30,-9,6000)]}
    for i,f0 in enumerate(LADDER)],"the level's ladder bell (Tormai bronze): one step up a D pentatonic ladder per level")
rec("hero_down","heroes","procedural",[{"layers":[
    bowl(146.83,1.8,2.0,0,-1,2500), bowl(174.61,1.6,2.0,60,-4,2500),
    {"synth":"rumble","dur":1.4,"lp":120,"decay":0.6,"gain_db":-9},
    {"src":IS+"impactSoft_heavy_00%d.ogg"%a,"pitch":0.6,"gain_db":-6}]}
    for a in (0,2)],"hero down sting: a low procedural minor third on D over a rumble, a soft thud (Kenney CC0)")
rec("hero_revive","heroes","procedural",[{"layers":[
    bowl(293.66,1.6,2.0,0,-2,6000), bowl(440.0,1.4,1.8,40,-5,7000), bowl(587.33,1.2,1.6,80,-7,8000),
    {"synth":"noise","dur":1.0,"hp":4000,"decay":0.6,"attack":0.05,"gain_db":-30}]}
    for _ in range(2)],"revive: an open procedural chord on D with a soft shimmer")
# hero abilities (juice ABL-*, Playtest 3): procedural one-shots plus CC0 layers
rec("ab_cast","heroes","procedural",[{"layers":[
    {"synth":"noise","dur":0.35,"lp":2500,"hp":300,"decay":0.12,"attack":0.08,"gain_db":-10},
    bowl(f0,0.4,0.5,40,-12,6000)]}
    for f0 in (880.0,987.77)],"cast swell: a soft procedural whoosh and a faint bell")
rec("ab_heal","heroes","procedural",[{"layers":[
    bowl(783.99,0.8,1.1,0,-3,9000), bowl(1174.66,0.7,1.0,90,-6,9000), tick(5200,0,-16)]}
    for _ in range(2)],"linden balm: two bright procedural bells a fifth apart")
rec("ab_brace","heroes","cc0",[{"layers":[
    {"src":IS+"impactPlate_medium_00%d.ogg"%a,"pitch":0.85},
    {"src":IS+"impactPlank_medium_00%d.ogg"%b,"pitch":0.7,"gain_db":-5,"offset_ms":20},
    {"synth":"thump","f0":70,"f1":40,"decay":0.12,"dur":0.35,"gain_db":-6}]}
    for a,b in ((0,1),(2,3))],"brace the wheel: a shield planted, plate and timber (Kenney CC0) + sub thump")
rec("ab_ring","heroes","procedural",[{"layers":[
    bowl(196.0,2.0,2.2,0,0,4000), bowl(293.66,1.6,2.0,80,-4,5000),
    {"src":IS+"impactWood_heavy_00%d.ogg"%a,"pitch":0.8,"gain_db":-6},
    {"src":IS+"impactWood_heavy_00%d.ogg"%b,"pitch":0.75,"gain_db":-8,"offset_ms":140}]}
    for a,b in ((0,2),(1,3))],"the wagon ring: wagons drawn round (Kenney CC0 wood) under a procedural bronze chord")
rec("ab_fire","heroes","procedural",[{"layers":[
    {"synth":"thump","f0":80,"f1":45,"decay":0.15,"dur":0.4,"gain_db":-2},
    {"synth":"noise","dur":0.9,"lp":3000,"hp":200,"decay":0.35,"attack":0.01,"gain_db":-6},
    {"src":IS+"impactGlass_heavy_00%d.ogg"%a,"pitch":1.1,"gain_db":-8}]}
    for a in (0,2)],"naphtha flask: a glass burst (Kenney CC0) and a procedural fire whoosh")
rec("ab_lash","heroes","procedural",[{"layers":[
    {"synth":"noise","dur":0.25,"hp":1500,"decay":0.06,"attack":0.04,"gain_db":-6},
    {"src":IS+"impactPunch_medium_00%d.ogg"%a,"pitch":1.3,"offset_ms":120,"gain_db":-4}]}
    for a in (1,3)],"braid lash: a whip whoosh (procedural) and its crack (Kenney CC0)")
rec("ab_veil","heroes","procedural",[{"layers":[
    {"synth":"noise","dur":0.8,"lp":1800,"hp":150,"decay":0.3,"attack":0.03,"gain_db":-6}]}
    for _ in range(2)],"dust veil: a soft procedural dust puff")
rec("ab_glint","heroes","procedural",[{"layers":[
    bowl(2093.0,0.35,0.6,0,-2,12000), bowl(3135.96,0.25,0.5,20,-8,12000), tick(7000,0,-12)]}
    for _ in range(2)],"sunglint: a bright procedural ping")
rec("ab_window","heroes","procedural",[{"layers":[
    bowl(659.25,1.4,1.8,0,-3,7000), bowl(987.77,1.2,1.6,60,-7,8000),
    {"synth":"noise","dur":1.2,"hp":5000,"decay":0.5,"attack":0.2,"gain_db":-36}]}
    for _ in range(2)],"bronze window: a polished bowl with a shimmer")
rec("ab_dark","heroes","procedural",[{"layers":[
    {"synth":"rumble","dur":2.0,"lp":120,"decay":0.9,"attack":0.3,"gain_db":-4},
    bowl(110.0,2.0,2.2,0,-6,1800),
    {"synth":"noise","dur":1.2,"lp":900,"hp":100,"decay":0.5,"attack":0.4,"gain_db":-12}]}
    for _ in range(2)],"swallowed sun: a low procedural swell into darkness")
rec("ab_summon","heroes","cc0",[{"layers":[
    {"src":IS+"impactSoft_heavy_00%d.ogg"%a,"pitch":0.8},
    bowl(392.0,1.0,1.2,30,-8,5000)]}
    for a in (1,4)],"a summon arrives: a soft heavy thud (Kenney CC0) and a bowl")
json.dump({"_doc":"Recipes for tools/audio/build_layered_sfx.py: CC0 (Kenney, assets_src/audio/cc0/kenney, licence files beside them) and procedural placeholder takes. A take with a 'name' is a kit item: it is written as <id>_<name>_<nn>.wav.","recipes":R},open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'layered_recipes.json'),'w'),indent=1)
print(len(R))
