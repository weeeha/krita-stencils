"""Generate face stencils per person.

neutral   : text only, fixed seed per person, straight to camera
emotions  : img2img from the neutral photo (same framing and identity), DENOISE
angles    : text only, same seed and description, weighted angle wording (IP-Adapter flattened every angle to front in tests)
usage: python3 stencils/faces.py [person_slug ...]
Output in work/faces/<person>/<slug>_photo.png, _line.png, _sketch.png. Existing tiles are skipped.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import comfy
from sketch import to_sketch
from specs import ANGLES, EMOTIONS, FACE_TAIL, PEOPLE

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "work", "faces")
DENOISE = float(os.environ.get("FACE_DENOISE", 0.8))
EMO_NEG = "neutral expression, calm, expressionless, relaxed face"
ANGLE_NEG = "front view, looking at the camera, full body, torso, sky, outdoors"
SEED_OFFSET = int(os.environ.get("SEED_OFFSET", 0))


def tile(base, prompt, seed, **kw):
    if os.path.exists(base + "_sketch.png"):
        return "skip"
    t = time.time()
    comfy.generate(prompt, base + "_photo.png", base + "_line.png", w=1024, h=1024, seed=seed,
                   line_res=2048, line_method="teed", tag="f" + os.path.basename(os.path.dirname(base)) + os.path.basename(base), **kw)
    to_sketch(base + "_line.png", base + "_sketch.png")
    return f"{time.time() - t:.0f}s"


def person(pi, slug, desc):
    d = os.path.join(ROOT, slug); os.makedirs(d, exist_ok=True)
    seed = 7000 + 37 * pi + SEED_OFFSET
    head = f"close-up head and shoulders portrait photograph of {desc}"
    neutral = os.path.join(d, EMOTIONS[0][0])
    print(slug, "neutral", tile(neutral, f"{head}, {EMOTIONS[0][1]}, looking straight into the camera, head straight, symmetrical front view, {FACE_TAIL}", seed), flush=True)
    ref = comfy.upload(neutral + "_photo.png")
    for e, txt in EMOTIONS[1:]:
        print(slug, e, tile(os.path.join(d, e), f"{head}, ({txt}:1.5), strong facial expression, looking at the camera, {FACE_TAIL}",
                            seed, init_image=ref, denoise=DENOISE, neg_extra=EMO_NEG), flush=True)
    close = f"(close-up head and shoulders portrait:1.3) photograph of {desc}"
    for a, txt in ANGLES:
        if a == "11_front":
            p, neg = f"{head}, neutral expression, {txt}, {FACE_TAIL}", ""
        else:
            p, neg = f"{close}, neutral expression, ({txt}:1.4), ({FACE_TAIL}:1.2)", ANGLE_NEG
        print(slug, a, tile(os.path.join(d, a), p, seed, neg_extra=neg), flush=True)


if __name__ == "__main__":
    want = set(sys.argv[1:])
    for pi, (slug, desc) in enumerate(PEOPLE):
        if not want or slug in want:
            person(pi, slug, desc)
