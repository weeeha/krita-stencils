"""Spike 3 on person 02: weighted emotions at denoise 0.8 vs 0.88, weighted camera angles."""
import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import comfy
from sketch import to_sketch
from specs import PEOPLE, FACE_TAIL
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "work", "test_faces3"); os.makedirs(OUT, exist_ok=True)
slug, desc = PEOPLE[1]
seed = 7000 + 37 * 1
head = f"close-up head and shoulders portrait photograph of {desc}"
ref = comfy.upload(os.path.join(HERE, "..", "work", "faces", slug, "01_neutral_photo.png"))
done = []

def go(name, prompt, **kw):
    t = time.time()
    comfy.generate(prompt, f"{OUT}/{name}_photo.png", f"{OUT}/{name}_line.png", w=1024, h=1024, seed=seed,
                   line_res=2048, line_method="teed", tag=f"tf3_{name}", **kw)
    to_sketch(f"{OUT}/{name}_line.png", f"{OUT}/{name}_sketch.png"); done.append(name)
    print(name, f"{time.time()-t:.0f}s", flush=True)

EMO = [("sad", "deeply sad, frowning, inner eyebrows raised, lower lip pushed out"),
       ("angry", "furious, furrowed brow, shouting, teeth showing"),
       ("afraid", "terrified, eyes wide open, eyebrows pulled up, mouth stretched open"),
       ("disgusted", "disgusted, nose wrinkled, upper lip raised")]
for dn in (0.8, 0.88):
    for e, txt in EMO:
        go(f"{e}_{dn}", f"{head}, ({txt}:1.5), strong facial expression, looking at the camera, {FACE_TAIL}",
           init_image=ref, denoise=dn, neg_extra="neutral expression, calm, expressionless, relaxed face")
for a, txt in [("three_quarter_left", "(three-quarter view, head turned 45 degrees to the left:1.5)"),
               ("looking_up", "(low angle shot from below, head tilted back looking up at the sky:1.5), chin raised"),
               ("looking_down", "(high angle shot from above, head bowed looking down at the floor:1.5)")]:
    go(a, f"{head}, neutral expression, {txt}, {FACE_TAIL}", neg_extra="front view, looking at the camera, facing the camera")

C = 230
s = Image.new("RGB", (C * len(done), 2 * C + 20), "white"); d = ImageDraw.Draw(s)
for i, n in enumerate(done):
    for r, k in enumerate(["photo", "sketch"]):
        im = Image.open(f"{OUT}/{n}_{k}.png").convert("RGB"); im.thumbnail((C, C)); s.paste(im, (i * C, 20 + r * C))
    d.text((i * C + 3, 3), n, fill="black")
s.save(os.path.join(OUT, "..", "sheet_test_faces3.png"))
