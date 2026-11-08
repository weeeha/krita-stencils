"""Generate body stencils.

Per tile: prompt-posed photo -> anatomy + action check (check.py) -> retry with a new seed.
After PROMPT_TRIES failures the remaining tries are guided by a pose that already passed for
another character (work/pose_bank/<action>.png), so a stubborn action still comes out right.

usage: python3 stencils/bodies.py [character_slug ...]   (default: all)
Output in work/bodies/<char>/: <action>_photo.png, _line.png, _sketch.png, _kps.json, _pose.png,
plus <action>_ok or <action>_flagged. Every try is logged to work/bodies/log.jsonl.
Re-running skips tiles that have _ok; flagged tiles are retried with SEED_OFFSET seeds.
"""
import glob, json, os, shutil, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import comfy
from check import body_check
from sketch import to_sketch
from specs import ACTIONS, BODY_TAIL, CHARACTERS

WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "work")
ROOT = os.path.join(WORK, "bodies")
BANK = os.path.join(WORK, "pose_bank")
PROMPT_TRIES, GUIDED_TRIES = 3, 3
SEED_OFFSET = int(os.environ.get("SEED_OFFSET", 0))
_uploaded = {}


def bank_pose(act):
    p = os.path.join(BANK, f"{act}.png")
    if not os.path.exists(p):
        return None
    if p not in _uploaded:
        _uploaded[p] = comfy.upload(p)
    return _uploaded[p]


def one(ci, char, desc, ai, act, phrase, orient):
    d = os.path.join(ROOT, char); os.makedirs(d, exist_ok=True)
    base = os.path.join(d, act)
    if os.path.exists(base + "_ok"):
        return "skip"
    w, h = (1216, 832) if orient == "landscape" else (832, 1216)
    prompt = f"full body photograph of {desc}, {phrase}, {BODY_TAIL}"
    best = None
    for t in range(PROMPT_TRIES + GUIDED_TRIES):
        guide = bank_pose(act) if t >= PROMPT_TRIES else None
        seed = 100000 * (ci + 1) + 100 * ai + t + SEED_OFFSET
        t0 = time.time()
        stem = f"{base}_try{t}"
        comfy.generate(prompt, f"{stem}_photo.png", f"{stem}_line.png", f"{stem}_kps.json", w=w, h=h, seed=seed,
                       line_res=min(w, h) * 2, line_method="pidinet", pose_image=guide, pose_strength=0.7,
                       tag=f"b{char}_{act}_{t}_{SEED_OFFSET}")
        ok, why, m = body_check(json.load(open(f"{stem}_kps.json")), w, h, landscape=orient == "landscape", action=act)
        rec = {"char": char, "action": act, "try": t, "guided": bool(guide), "seed": seed, "ok": ok, "why": why, "m": m,
               "s": round(time.time() - t0)}
        open(os.path.join(ROOT, "log.jsonl"), "a").write(json.dumps(rec) + "\n")
        print(json.dumps(rec), flush=True)
        if best is None or len(why) < len(best[1]):
            best = (t, why)
        if ok:
            break
    t = best[0]
    for suf in ("photo.png", "line.png", "kps.json", "pose.png"):
        os.replace(f"{base}_try{t}_{suf}", f"{base}_{suf}")
    for f in glob.glob(f"{base}_try*"):
        os.remove(f)
    for f in glob.glob(base + "_flagged"):
        os.remove(f)
    to_sketch(f"{base}_line.png", f"{base}_sketch.png")
    if not best[1]:
        open(base + "_ok", "w").write("")
        os.makedirs(BANK, exist_ok=True)
        if not os.path.exists(os.path.join(BANK, f"{act}.png")):
            shutil.copy(f"{base}_pose.png", os.path.join(BANK, f"{act}.png"))
        return "ok"
    open(base + "_flagged", "w").write(json.dumps(best[1]))
    return "flagged " + "; ".join(best[1])


if __name__ == "__main__":
    want = set(sys.argv[1:])
    for ci, (char, desc) in enumerate(CHARACTERS):
        if want and char not in want:
            continue
        for ai, (act, phrase, orient) in enumerate(ACTIONS):
            print(char, act, one(ci, char, desc, ai, act, phrase, orient), flush=True)
