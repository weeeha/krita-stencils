"""Spike: one person, neutral + emotions via img2img + angles via IP-Adapter, coarse vs fine lines."""
import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import comfy
from sketch import to_sketch

OUT = os.path.join(os.path.dirname(__file__), "..", "work", "test_faces")
os.makedirs(OUT, exist_ok=True)
P = "close-up head and shoulders portrait photograph of a 45 year old woman, shoulder-length dark hair, light freckles"
TAIL = "plain light grey studio background, soft even lighting, 85mm lens, sharp focus, realistic photo, high detail"
SEED = 2024

def go(name, prompt, **kw):
    t = time.time()
    comfy.generate(prompt, f"{OUT}/{name}_photo.png", f"{OUT}/{name}_line.png", w=1024, h=1024, seed=SEED,
                   line_res=2048, tag=f"tf_{name}", **kw)
    to_sketch(f"{OUT}/{name}_line.png", f"{OUT}/{name}_sketch.png")
    print(name, f"{time.time()-t:.0f}s", flush=True)

go("neutral_fine", f"{P}, neutral expression, facing the camera, {TAIL}", coarse=False)
go("neutral", f"{P}, neutral expression, facing the camera, {TAIL}", coarse=True)
ref = comfy.upload(f"{OUT}/neutral_photo.png")
for emo, txt in [("happy", "big happy smile showing teeth"), ("sad", "sad, eyes glistening, corners of the mouth down"),
                 ("angry", "angry, furrowed brow, shouting"), ("surprised", "surprised, eyes wide, mouth open")]:
    go(emo, f"{P}, {txt}, facing the camera, {TAIL}", coarse=True, init_image=ref, denoise=0.6)
for ang, txt in [("three_quarter_left", "head turned three-quarter to the left"), ("profile_right", "head in full side profile facing right"),
                 ("looking_up", "head tilted back looking up, seen from below"), ("looking_down", "head tilted down looking down, seen from above")]:
    go(ang, f"{P}, neutral expression, {txt}, {TAIL}", coarse=True, ipadapter_image=ref, ipadapter_weight=0.6)
