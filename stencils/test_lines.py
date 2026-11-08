"""Compare line extractors on the same photos (no sampling, seconds per image)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import comfy
from sketch import to_sketch
from PIL import Image, ImageDraw

W = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "work")
OUT = os.path.join(W, "test_lines"); os.makedirs(OUT, exist_ok=True)
SRC = {"face": f"{W}/test_faces/neutral_photo.png", "body": f"{W}/bodies/01_man_30s/02_walking_photo.png"}

VARIANTS = [
    ("realistic_fine", "LineArtPreprocessor", {"coarse": "disable"}, 0),
    ("realistic_fine_blur", "LineArtPreprocessor", {"coarse": "disable"}, 2),
    ("standard", "LineartStandardPreprocessor", {"guassian_sigma": 6.0, "intensity_threshold": 8}, 0),
    ("anime", "AnimeLineArtPreprocessor", {}, 0),
    ("manga", "Manga2Anime_LineArt_Preprocessor", {}, 0),
    ("teed", "TEEDPreprocessor", {"safe_steps": 2}, 0),
    ("pidinet", "PiDiNetPreprocessor", {"safe": "enable"}, 0),
]

rows = []
for key, path in SRC.items():
    ref = comfy.upload(path)
    w, h = Image.open(path).size
    cells = []
    for name, cls, extra, blur in VARIANTS:
        x = comfy.G()
        li = x.add("LoadImage", image=ref)
        img = [x.add("ImageScaleBy", image=[li, 0], upscale_method="lanczos", scale_by=2.0), 0]
        if blur:
            img = [x.add("ImageBlur", image=img, blur_radius=blur, sigma=1.0), 0]
        p = x.add(cls, image=img, resolution=min(w, h) * 2, **extra)
        s = x.add("SaveImage", images=[p, 0], filename_prefix=f"stencil2/tl_{key}_{name}")
        outs = comfy.run(x.g)
        lp = f"{OUT}/{key}_{name}_line.png"
        comfy.save_outputs(outs, {s: lp})
        to_sketch(lp, f"{OUT}/{key}_{name}_sketch.png")
        cells.append((name, f"{OUT}/{key}_{name}_sketch.png"))
        print(key, name, flush=True)
    rows.append(cells)

C = 340
sheet = Image.new("RGB", (C * len(VARIANTS), (C + 22) * 2 + 140), "white"); d = ImageDraw.Draw(sheet)
y = 0
for r, key in zip(rows, SRC):
    hh = C if key == "face" else C + 140
    for i, (name, p) in enumerate(r):
        im = Image.open(p).convert("RGB"); im.thumbnail((C, hh)); sheet.paste(im, (i * C, y + 22)); d.text((i * C + 4, y + 4), name, fill="black")
    y += hh + 22
sheet.save(f"{W}/sheet_test_lines.png")
