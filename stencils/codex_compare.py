"""Turn the Codex sample into stencils (same extractors as local), check body poses, build a comparison sheet."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import comfy
from check import body_check
from sketch import to_sketch
from specs import ACTIONS
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(HERE, "..", "work")
CX = os.path.join(W, "codex")
ORIENT = {a: o for a, _, o in ACTIONS}
FACES = ["04_sad", "05_crying", "06_angry", "08_afraid", "09_disgusted", "10_thinking",
         "12_three_quarter_left", "15_profile_right", "16_looking_up", "17_looking_down"]


def extract(src, kind):
    """Returns (line_path, kps or None)."""
    w, h = Image.open(src).size
    up = comfy.upload(src)
    x = comfy.G()
    li = x.add("LoadImage", image=up)
    big = x.add("ImageScaleBy", image=[li, 0], upscale_method="lanczos", scale_by=2.0)
    if kind == "body":
        la = x.add("PiDiNetPreprocessor", image=[big, 0], safe="enable", resolution=min(w, h) * 2)
    else:
        la = x.add("TEEDPreprocessor", image=[big, 0], safe_steps=2, resolution=min(w, h) * 2)
    tag = "cx_" + os.path.basename(src)[:-4]
    sv = x.add("SaveImage", images=[la, 0], filename_prefix=f"stencil2/{tag}_line")
    if kind == "body":
        op = x.add("OpenposePreprocessor", image=[li, 0], detect_hand="enable", detect_body="enable", detect_face="disable", resolution=1024)
        x.add("SavePoseKpsAsJsonFile", pose_kps=[op, 1], filename_prefix=f"stencil2/{tag}_kps")
    outs = comfy.run(x.g)
    line = src[:-4] + "_line.png"
    comfy.save_outputs(outs, {sv: line})
    to_sketch(line, src[:-4] + "_sketch.png")
    return line, (comfy.fetch_json("stencil2", f"{tag}_kps") if kind == "body" else None)


def main():
    results = {}
    for act, _, orient in ACTIONS:
        src = os.path.join(CX, f"body_{act}.png")
        if not os.path.exists(src):
            results[act] = "missing"; continue
        _, kps = extract(src, "body")
        w, h = Image.open(src).size
        ok, why, m = body_check(kps, w, h, landscape=orient == "landscape", action=act)
        results[act] = "OK" if ok else "; ".join(why)
        print("GPT", act, results[act], flush=True)
    for f in FACES:
        src = os.path.join(CX, f"face_{f}.png")
        if os.path.exists(src):
            extract(src, "face"); print("GPT face", f, flush=True)
    json.dump(results, open(os.path.join(CX, "check.json"), "w"), indent=1)

    # sheet: per action local vs gpt; per face local vs gpt
    C = (190, 270); F = 190; L = 16
    rows = [("LOCAL bodies (01 man)", [(os.path.join(W, "bodies", "01_man_30s", f"{a}_sketch.png"), a[3:]) for a, _, _ in ACTIONS], C),
            ("GPT bodies (same man, same actions)", [(os.path.join(CX, f"body_{a}_sketch.png"), f"{a[3:]} {'OK' if results.get(a) == 'OK' else 'X'}") for a, _, _ in ACTIONS], C),
            ("LOCAL faces (02 man)", [(os.path.join(W, "faces", "02_man_30", f"{f}_sketch.png"), f[3:]) for f in FACES], (F, F)),
            ("GPT faces (local neutral as reference)", [(os.path.join(CX, f"face_{f}_sketch.png"), f[3:]) for f in FACES], (F, F))]
    width = 10 * C[0]
    height = sum(c[1] + 2 * L for _, _, c in rows)
    s = Image.new("RGB", (width, height), "white"); d = ImageDraw.Draw(s); y = 0
    for title, items, cell in rows:
        d.text((4, y + 2), title, fill="black")
        for i, (p, lab) in enumerate(items):
            x0 = i * C[0]
            d.text((x0 + 4, y + L + 2), lab, fill="black")
            if os.path.exists(p):
                im = Image.open(p).convert("RGB"); im.thumbnail(cell)
                s.paste(im, (x0 + (C[0] - im.width) // 2, y + 2 * L))
        y += cell[1] + 2 * L
    s.save(os.path.join(W, "compare_local_vs_gpt_v2.png"))
    print("sheet saved", s.size)


if __name__ == "__main__":
    main()
