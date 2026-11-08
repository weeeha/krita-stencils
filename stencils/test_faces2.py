"""Spike 2: clean skin, TEED lines, img2img denoise 0.72, angles with IP-Adapter 0.3 vs none."""
import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import comfy
from sketch import to_sketch
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "work", "test_faces2")
os.makedirs(OUT, exist_ok=True)
P = "close-up head and shoulders portrait photograph of a 45 year old woman, shoulder-length dark hair"
TAIL = "plain light grey studio background, soft even lighting, 85mm lens, sharp focus, realistic photo, high detail"
SEED = 2024
done = []

def go(name, prompt, **kw):
    t = time.time()
    comfy.generate(prompt, f"{OUT}/{name}_photo.png", f"{OUT}/{name}_line.png", w=1024, h=1024, seed=SEED,
                   line_res=2048, line_method="teed", tag=f"tf2_{name}", **kw)
    to_sketch(f"{OUT}/{name}_line.png", f"{OUT}/{name}_sketch.png")
    done.append(name); print(name, f"{time.time()-t:.0f}s", flush=True)

go("neutral", f"{P}, neutral expression, facing the camera, {TAIL}")
ref = comfy.upload(f"{OUT}/neutral_photo.png")
for emo, txt in [("sad", "sad, eyes glistening, corners of the mouth turned down"), ("angry", "angry, furrowed brow, shouting"),
                 ("surprised", "surprised, eyebrows raised, eyes wide, mouth open")]:
    go(emo, f"{P}, {txt}, facing the camera, {TAIL}", init_image=ref, denoise=0.72)
for ang, txt in [("profile", "head in full side profile facing right"), ("three_q", "head turned three-quarter to the left")]:
    go(f"{ang}_ipa03", f"{P}, neutral expression, {txt}, {TAIL}", ipadapter_image=ref, ipadapter_weight=0.3)
    go(f"{ang}_text", f"{P}, neutral expression, {txt}, {TAIL}")

C = 280
s = Image.new("RGB", (C * len(done), C * 2 + 22), "white"); d = ImageDraw.Draw(s)
for i, n in enumerate(done):
    for r, k in enumerate(["photo", "sketch"]):
        im = Image.open(f"{OUT}/{n}_{k}.png").convert("RGB"); im.thumbnail((C, C)); s.paste(im, (i * C, 22 + r * C))
    d.text((i * C + 4, 4), n, fill="black")
s.save(os.path.join(OUT, "..", "sheet_test_faces2.png"))
