"""What gets drawn: 10 bodies x 10 actions, 10 faces x (10 emotions + 8 angles)."""

BODY_TAIL = ("whole body visible from head to feet with empty space around the figure, plain light grey studio "
             "background, even soft lighting, 50mm lens, sharp focus, realistic photo, natural anatomy, high detail")

# (slug, description). Adults only, so one proportion rule (7 to 8 heads) holds for all.
CHARACTERS = [
    ("01_man_30s", "a 30 year old man, average athletic build, short dark hair, fitted grey t-shirt, dark jeans, white sneakers"),
    ("02_woman_20s", "a 25 year old slim woman, long hair in a ponytail, fitted long-sleeve top, leggings, sneakers"),
    ("03_man_60s", "a 60 year old man, sturdy build, grey beard, short grey hair, button shirt, chinos, leather shoes"),
    ("04_woman_40s", "a 40 year old woman, average build, short bob haircut, plain t-shirt, straight jeans, flat shoes"),
    ("05_man_heavy", "a 45 year old heavyset man, bald, polo shirt, cargo trousers, sneakers"),
    ("06_woman_athlete", "a 30 year old muscular athletic woman, braided hair, sports bra, running shorts, trainers"),
    ("07_man_tall_thin", "a 35 year old tall thin man, curly hair, glasses, sweater, slim trousers, boots"),
    ("08_woman_70s", "a 70 year old woman, slender, white hair in a bun, cardigan, long skirt, flat shoes"),
    ("09_man_muscular", "a 28 year old muscular man, buzz cut, tank top, track pants, sneakers"),
    ("10_woman_curvy", "a 35 year old curvy plus-size woman, shoulder-length wavy hair, fitted dress, flat sandals"),
]

# (slug, action phrase, orientation)
ACTIONS = [
    ("01_standing", "standing relaxed, weight on one leg, arms at the sides, facing the camera", "portrait"),
    ("02_walking", "walking towards the camera, mid stride, arms swinging naturally, three-quarter view", "portrait"),
    ("03_running", "sprinting, side view, mid-stride with the front knee driving up and the back leg pushing off, elbows bent, one arm swinging forward and the other back, torso leaning forward", "portrait"),
    ("04_sitting", "sitting on a simple wooden stool, three-quarter view, relaxed", "portrait"),
    ("05_jumping", "jumping in the air, both feet off the ground, arms raised, joyful", "portrait"),
    ("06_crouching", "crouching low on the balls of the feet, knees bent, one hand touching the floor, three-quarter view", "portrait"),
    ("07_reaching", "stretching one arm straight up with the hand high above the head as if reaching a high shelf, standing on tiptoe, looking up, three-quarter view", "portrait"),
    ("08_punching", "throwing a straight punch towards the camera, fighting stance, three-quarter view", "portrait"),
    ("09_lying", "lying flat on the back on the floor, whole body horizontal, head resting on the floor, one knee bent up, seen from the side", "landscape"),
    ("10_pointing", "standing and pointing into the distance with an outstretched arm, side view", "portrait"),
]

FACE_TAIL = "plain light grey studio background, soft even lighting, 85mm lens, sharp focus, realistic photo, high detail"

PEOPLE = [
    ("01_woman_45", "a 45 year old woman, shoulder-length dark hair"),
    ("02_man_30", "a 30 year old man, short brown hair, light stubble"),
    ("03_woman_20", "a 22 year old woman, long straight blonde hair"),
    ("04_man_65", "a 65 year old man, white beard, receding grey hair"),
    ("05_woman_35_curly", "a 35 year old black woman, natural curly hair"),
    ("06_man_40_asian", "a 40 year old east asian man, short black hair, clean shaven"),
    ("07_woman_75", "a 75 year old woman, short white hair, wrinkles"),
    ("08_boy_12", "a 12 year old boy, messy hair"),
    ("09_man_25_beard", "a 25 year old man, long dark hair tied back, full beard"),
    ("10_woman_50_glasses", "a 50 year old woman, grey pixie cut, round glasses"),
]

# Emotions are reworked from the neutral photo (img2img 0.8, wording weighted 1.5), so framing and identity hold.
EMOTIONS = [
    ("01_neutral", "neutral expression"),
    ("02_happy", "happy, warm smile, cheeks raised"),
    ("03_laughing", "laughing out loud, eyes squinting, mouth wide open"),
    ("04_sad", "deeply sad, frowning, inner eyebrows raised, lower lip pushed out"),
    ("05_crying", "crying hard, tears running down the cheeks, face crumpled, mouth turned down"),
    ("06_angry", "furious, furrowed brow, shouting, teeth showing"),
    ("07_surprised", "astonished, eyebrows raised high, eyes wide, mouth open in an O"),
    ("08_afraid", "terrified, eyes wide open, eyebrows pulled up, mouth stretched open"),
    ("09_disgusted", "disgusted, nose wrinkled, upper lip raised"),
    ("10_thinking", "deep in thought, eyes looking up to the side, lips pressed, one eyebrow raised"),
]

# Angles are new generations from the same seed and description, wording weighted 1.4
# (an IP-Adapter guide flattened every angle to front, unweighted wording was ignored).
ANGLES = [
    ("11_front", "looking straight into the camera, head straight, symmetrical front view"),
    ("12_three_quarter_left", "three-quarter view, head turned 45 degrees to the left"),
    ("13_three_quarter_right", "three-quarter view, head turned 45 degrees to the right"),
    ("14_profile_left", "head in full side profile facing left"),
    ("15_profile_right", "head in full side profile facing right"),
    ("16_looking_up", "head tilted back, chin raised, looking up, seen slightly from below"),
    ("17_looking_down", "head bowed, chin down, eyes looking down, seen slightly from above"),
    ("18_back_three_quarter", "seen from behind over the shoulder, head turned slightly showing the cheek and ear"),
]

# ---------- action-scene set (GPT via Codex, see stencils/gpt_upgrade.py) ----------
ACTION_CAST = [
    ("a_man_30", "a 30 year old man, athletic build, short dark hair, black t-shirt, cargo trousers, combat boots"),
    ("b_woman_28", "a 28 year old athletic woman, hair in a tight bun, fitted jacket, cargo trousers, boots"),
    ("c_man_40", "a 40 year old stocky muscular man, short beard, vest over a grey shirt, cargo trousers, boots"),
    ("d_woman_25", "a 25 year old lean woman, short undercut hair, hoodie, joggers, trainers"),
    ("e_man_35", "a 35 year old tall man, shaved head, long dark coat, dark trousers, boots"),
]

# (slug, phrase, orientation, people). Two-person scenes pair cast i with cast i+1.
ACTION_SCENES = [
    ("01_sprint_rifle", "sprinting forward holding a rifle across the chest with both hands, side view, mid-stride, front knee high, torso leaning forward", "portrait", 1),
    ("02_aim_standing", "standing and aiming a rifle, stock against the shoulder, cheek on the stock, feet apart, side view", "portrait", 1),
    ("03_aim_kneeling", "kneeling on one knee aiming a rifle, the other foot planted forward, three-quarter view", "portrait", 1),
    ("04_pistol_aim", "standing in a shooting stance aiming a pistol with both arms extended forward, knees slightly bent, three-quarter view", "portrait", 1),
    ("05_grenade_throw", "throwing a grenade overarm, throwing arm cocked back behind the head, other arm pointing forward, weight on the back foot, side view", "portrait", 1),
    ("06_taking_cover", "crouching low and moving to cover, holding a rifle pointed down, looking back over the shoulder, three-quarter view", "portrait", 1),
    ("07_flying_kick", "high side kick, kicking leg extended straight out at hip height, arms raised in guard, side view", "portrait", 1),
    ("08_dive_roll", "diving forward to the floor, body almost horizontal in the air, both arms reaching ahead", "landscape", 1),
    ("09_fist_fight", "two people in a fist fight: one throws a punch with the arm fully extended, the other leans back and blocks with raised forearms, both seen from the side", "landscape", 2),
    ("10_grapple", "two people wrestling: one grabs the other around the waist, the other pushes back with both hands on the shoulders, both knees bent, side view", "landscape", 2),
]

# ---------- film sheets (12 poses per GPT image, see stencils/gpt_sheets.py) ----------
# Nick's films: late 80s to mid 90s Montreal, everyday people near dead machines. Walking, scavenging, repairing, running away.
FILM_CAST = [
    ("a_man_40", "a 40 year old man with a short beard, knit toque, worn brown canvas work jacket, jeans, work boots, small backpack"),
    ("b_woman_30", "a 30 year old woman, long dark hair, early 90s puffy winter parka with a scarf, corduroy trousers, snow boots"),
    ("c_teen_15", "a 15 year old boy, early 90s jean jacket over a hoodie, baggy jeans, high-top sneakers, backpack"),
    ("d_man_65", "a 65 year old man, grey stubble, flat cap, stained navy mechanic coveralls, old leather work boots"),
    ("e_woman_25", "a 25 year old woman, short hair, faded windbreaker, cargo trousers, hiking boots, messenger bag"),
]
FILM_A = [  # getting by
    ("31_walk_away", "walking away from the camera, seen from behind, hands in pockets"),
    ("32_carry_bag", "walking towards the camera carrying a heavy duffel bag on one shoulder, leaning against the weight"),
    ("33_trudge_snow", "trudging through deep snow, leaning forward, knees high"),
    ("34_dig_scrap", "crouching and digging through a pile of scrap metal on the ground"),
    ("35_pull_cable", "pulling a thick cable out of a pile with both hands, leaning back"),
    ("36_carry_pipe", "carrying a long metal pipe on one shoulder, side view"),
    ("37_repair_wrench", "kneeling on one knee repairing a machine part with a big wrench"),
    ("38_workbench", "standing at a cluttered workbench working with tools, side view"),
    ("39_tinker_crate", "sitting on a wooden crate tinkering with a small device held in the lap"),
    ("40_climb_fence", "climbing over a chain-link fence, one leg over the top"),
    ("41_push_cart", "pushing a shopping cart loaded with scrap"),
    ("42_look_up", "standing still and looking up at something huge, one hand shading the eyes, seen from behind"),
]
FILM_B = [  # running away
    ("51_run_away_back", "running away from the camera, seen from behind, mid-stride"),
    ("52_run_look_back", "sprinting, side view, looking back over the shoulder in fear"),
    ("53_run_at_camera", "running straight towards the camera in panic, arms pumping"),
    ("54_duck_cover", "running hunched over, ducking with both arms covering the head"),
    ("55_stumble", "stumbling forward while running, about to fall, arms thrown out"),
    ("56_vault", "vaulting over a low concrete barrier, one hand on top, legs swinging over"),
    ("57_crawl", "crawling fast on hands and knees, looking back"),
    ("58_hide_corner", "pressed flat against a wall corner, hiding, peeking around it"),
    ("59_ladder_climb", "scrambling up a metal ladder fast, looking down"),
    ("60_slide_snow", "sliding down a snowy slope on the back, arms out for balance"),
    ("61_haul_sled", "running while hauling a loaded sled by a rope over the shoulder"),
    ("62_catch_breath", "bent over catching breath, hands on knees, exhausted"),
]
FILM_C = [  # blast and aftermath, 4x3 sheet (wider cells for horizontal bodies); stunt framing, no blood or injuries
    ("81_blast_thrown_back", "thrown backwards off the feet by a blast, airborne, arms and legs flung forward"),
    ("82_blast_sideways", "blown sideways through the air, body almost horizontal, limbs trailing"),
    ("83_tumbling", "tumbling head over heels through the air"),
    ("84_hit_ground", "slamming onto the ground on the back, one arm and one leg still in the air"),
    ("85_face_down", "lying face down motionless, arms sprawled"),
    ("86_on_back", "lying on the back motionless, head turned aside, one arm flung out"),
    ("87_on_side", "lying on the side, curled slightly, still"),
    ("88_slumped_wall", "slumped sitting against a wall, head dropped forward, arms limp"),
    ("89_draped_barrier", "draped limp face down over a low concrete barrier"),
    ("90_crawl_dazed", "crawling away dazed on the stomach, one hand reaching forward"),
    ("91_kneel_dazed", "kneeling dazed, both hands holding the head"),
    ("92_sprawled_snow", "lying sprawled in the snow, motionless, face up"),
]
FILM_LANDSCAPE = {"57_crawl", "60_slide_snow", "82_blast_sideways", "83_tumbling", "84_hit_ground", "85_face_down",
                  "86_on_back", "87_on_side", "89_draped_barrier", "90_crawl_dazed", "92_sprawled_snow"}
FILM_DUOS = [  # 3x2 sheet per pair of FILM_CAST members (i, i+1)
    ("71_help_up", "one person pulls the other up off the ground by the hand"),
    ("72_carry_together", "the two carry a heavy car door between them"),
    ("73_boost_wall", "one person gives the other a boost up over a high wall with cupped hands"),
    ("74_run_together", "the two run away side by side, one pulling the other by the wrist"),
    ("75_workbench_two", "the two work together at one workbench, one holding a part while the other fixes it"),
    ("76_walk_talk", "the two walk side by side talking, one pointing ahead"),
]
