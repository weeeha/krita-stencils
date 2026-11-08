"""Proportion check + sketch conversion + contact sheet for the spike outputs."""
import json, os, glob, urllib.request, urllib.parse, math
from PIL import Image, ImageOps, ImageDraw, ImageFont
B = "http://127.0.0.1:18188"
D = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(D, "out")
POSES = ["standing", "walking", "running", "sitting", "reaching"]

def fetch_kps(pose):
    # list output dir for the json the workflow saved
    for n in range(1, 50):
        fn = f"body_{pose}_kps_{n:05d}.json"
        url = B + "/view?" + urllib.parse.urlencode({"filename": fn, "subfolder": "stencil", "type": "output"})
        try:
            return json.load(urllib.request.urlopen(url)), fn
        except Exception:
            continue
    return None, None

def latest_kps(pose):
    best = None
    for n in range(1, 50):
        fn = f"body_{pose}_kps_{n:05d}.json"
        url = B + "/view?" + urllib.parse.urlencode({"filename": fn, "subfolder": "stencil", "type": "output"})
        try:
            best = json.load(urllib.request.urlopen(url))
        except Exception:
            break
    return best

def to_sketch(line_png, out_png, grey=170):
    """LineArtPreprocessor gives white lines on black. Make dark-grey lines on white, light enough to draw over."""
    im = Image.open(line_png).convert("L")
    inv = ImageOps.invert(im)                      # black lines on white
    # lift blacks to grey: pixel = 255 - (255-p)*(255-grey)/255
    lut = [255 - int((255 - p) * (255 - grey) / 255) for p in range(256)]
    inv.point(lut).save(out_png)

def check_pose(pose):
    kps = latest_kps(pose)
    src = json.load(open(os.path.join(D, f"pose_{pose}.json")))
    if not kps or not kps[0].get("people"):
        return {"pose": pose, "detected": False}
    fr = kps[0]; cw, ch = fr["canvas_width"], fr["canvas_height"]
    p = fr["people"][0]["pose_keypoints_2d"]
    det = {i: (p[3*i] * 832, p[3*i+1] * 1216) for i in range(18) if p[3*i+2] > 0.3}
    devs = []
    for k, (x, y) in src.items():
        k = int(k)
        if k in det:
            devs.append(math.hypot(det[k][0] - x, det[k][1] - y))
    head = (det[1][1] - det[0][1]) / 0.97  # detector neck = shoulder line, ~0.97 head below the nose if 0 in det and 1 in det else None
    ank = max([det[i][1] for i in (10, 13) if i in det], default=None)
    heads_tall = None
    if head and ank and 0 in det:
        top = det[0][1] - 0.55 * head
        heads_tall = (ank + 0.3 * head - top) / head
    return {"pose": pose, "detected": True, "n_matched": len(devs), "mean_dev_px": round(sum(devs) / len(devs), 1) if devs else None,
            "max_dev_px": round(max(devs), 1) if devs else None, "head_px": round(head) if head else None, "heads_tall": round(heads_tall, 1) if heads_tall else None}

def sheet(items, out, cell=(320, 468), label_h=28):
    n = len(items); W = cell[0] * n; H = cell[1] + label_h
    s = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(s)
    for i, (path, label) in enumerate(items):
        im = Image.open(path).convert("RGB"); im.thumbnail(cell)
        s.paste(im, (i * cell[0] + (cell[0] - im.width) // 2, label_h))
        d.text((i * cell[0] + 6, 6), label, fill="black")
    s.save(out)

if __name__ == "__main__":
    results = []
    for pose in POSES:
        if os.path.exists(os.path.join(OUT, f"body_{pose}_line.png")):
            to_sketch(os.path.join(OUT, f"body_{pose}_line.png"), os.path.join(OUT, f"body_{pose}_sketch.png"))
            r = check_pose(pose); results.append(r); print(r)
    for i in range(5):
        lp = os.path.join(OUT, f"face_{i}_line.png")
        if os.path.exists(lp):
            to_sketch(lp, os.path.join(OUT, f"face_{i}_sketch.png"))
    json.dump(results, open(os.path.join(OUT, "pose_check.json"), "w"), indent=1)
    body_items = [(os.path.join(OUT, f"body_{p}_photo.png"), p) for p in POSES if os.path.exists(os.path.join(OUT, f"body_{p}_photo.png"))]
    if body_items:
        sheet(body_items, os.path.join(OUT, "sheet_bodies_photo.png"))
        sheet([(x.replace("_photo", "_sketch"), l + " " + (f"{r['heads_tall']} heads, dev {r['mean_dev_px']}px" if r.get("heads_tall") else "no pose")) for (x, l), r in zip(body_items, results)], os.path.join(OUT, "sheet_bodies_sketch.png"))
    face_items = [(os.path.join(OUT, f"face_{i}_photo.png"), f"face {i}") for i in range(5) if os.path.exists(os.path.join(OUT, f"face_{i}_photo.png"))]
    if face_items:
        sheet(face_items, os.path.join(OUT, "sheet_faces_photo.png"), cell=(320, 320))
        sheet([(x.replace("_photo", "_sketch"), l) for x, l in face_items], os.path.join(OUT, "sheet_faces_sketch.png"), cell=(320, 320))
