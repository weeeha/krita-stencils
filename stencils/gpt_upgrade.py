"""GPT (Codex, ChatGPT plan) stencils: the flagged bodies, the action-scene set, and all faces.

python3 stencils/gpt_upgrade.py bodies            redo every body tile marked _flagged (3 tries, keep the first that passes)
python3 stencils/gpt_upgrade.py actions [scene]   the action-scene set into work/actions/<scene>/
python3 stencils/gpt_upgrade.py faces [person]    GPT neutral from the local one, then 17 tiles from the GPT neutral
Raw GPT images live in work/gpt/; finished images and logs are kept, so a rerun resumes.
Local tiles that get replaced are copied to work/_old/ first. Lines come from ArtPC's ComfyUI (tunnel on 18188).
"""
import json, os, re, shutil, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
import comfy
from check import body_check
from sketch import to_sketch
from specs import ACTION_CAST, ACTION_SCENES, ACTIONS, ANGLES, CHARACTERS, EMOTIONS, PEOPLE
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.normpath(os.path.join(HERE, "..", "work"))
GPT, OLD = os.path.join(W, "gpt"), os.path.join(W, "_old")
SCRIPT = os.path.expanduser("~/.claude/skills/codex-image/scripts/codex-image.sh")
PAR = int(os.environ.get("GPT_PARALLEL", 4))
LOG_LOCK, COMFY_LOCK = threading.Lock(), threading.Lock()
abort, fails = threading.Event(), [0]
STUDIO = "plain light grey studio background, soft even lighting, realistic photo, correct human anatomy and proportions, no text"
FRAME = {"portrait": "whole body visible from head to feet with clear empty space above the head and below the feet, figure centred",
         "landscape": "whole body visible with clear empty space on every side, figure centred"}
BODY_FIX = {"08_punching": "throwing a straight punch, side view, the punching arm fully extended straight forward at shoulder "
                           "height with a closed fist, the other fist guarding the chin, feet apart in a fighting stance"}


def log(**kw):
    with LOG_LOCK, open(os.path.join(GPT, "log.jsonl"), "a") as f:
        f.write(json.dumps(kw) + "\n")


def codex(out, shape, prompt, ref=None):
    """One Codex image. False on failure; 4 failures in a row (not refusals) stop the whole run."""
    if os.path.exists(out):
        return True
    if abort.is_set():
        return False
    os.makedirs(os.path.dirname(out), exist_ok=True)
    errf = out[:-4] + ".log"
    cmd = ["bash", SCRIPT, "-o", out, "-s", shape] + (["-r", ref] if ref else []) + [prompt]
    try:
        with open(errf, "w") as e:
            rc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=e, timeout=480).returncode
    except subprocess.TimeoutExpired:
        rc = -9
    text = open(errf).read()
    m = re.search(r"tokens used\s*\n([\d,]+)", text)
    ok = rc == 0 and os.path.exists(out)
    log(out=os.path.relpath(out, W), rc=rc, tokens=int(m.group(1).replace(",", "")) if m else None)
    with LOG_LOCK:
        if ok or rc == 3:
            fails[0] = 0
        else:
            fails[0] += 1
            if fails[0] >= 4:
                abort.set()
                print("ABORT: 4 Codex failures in a row, see", errf, flush=True)
    return ok


def figure_box(im, thresh=14, min_hits=4):
    """Figure bounding box from edges: the vignetted studio backdrop is smooth, the figure is not."""
    import numpy as np
    from PIL import ImageFilter
    g = im.convert("L").filter(ImageFilter.GaussianBlur(2)).filter(ImageFilter.FIND_EDGES)
    e = np.array(g)
    e[:4, :] = e[-4:, :] = 0; e[:, :4] = e[:, -4:] = 0
    m = e > thresh
    rows, cols = np.where(m.sum(1) >= min_hits)[0], np.where(m.sum(0) >= min_hits)[0]
    if len(rows) == 0 or len(cols) == 0:
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def fit_crop(src, size, dst, margin=0.1):
    """Frame the GPT photo on the figure (plus a margin) at the tile's aspect, so figures fill the tile like local ones.
    Where that window runs past the image, the rest is padded with the backdrop colour.
    Returns the box of real image inside the tile, for clean_pad."""
    im = Image.open(src).convert("RGB")
    a = size[0] / size[1]
    bb = figure_box(im) or (0, 0, im.width, im.height)
    bw, bh = bb[2] - bb[0], bb[3] - bb[1]
    hh = max(bh * (1 + 2 * margin), bw * (1 + 2 * margin) / a, 0.45 * max(im.size) if a < 1 else 0.45 * im.height)
    ww = hh * a
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    # slide the window inside the image where it fits, centre it on the figure where it does not
    x0 = min(max(cx - ww / 2, 0), im.width - ww) if ww <= im.width else cx - ww / 2
    y0 = min(max(cy - hh / 2, 0), im.height - hh) if hh <= im.height else cy - hh / 2
    cx0, cy0 = max(0, round(x0)), max(0, round(y0))
    cx1, cy1 = min(im.width, round(x0 + ww)), min(im.height, round(y0 + hh))
    k = size[1] / hh
    part = im.crop((cx0, cy0, cx1, cy1))
    part = part.resize((max(1, round(part.width * k)), max(1, round(part.height * k))), Image.LANCZOS)
    px, py = round((cx0 - x0) * k), round((cy0 - y0) * k)
    edge = [part.getpixel((x, y)) for x in (0, part.width - 1) for y in range(0, part.height, 8)]
    bg = tuple(sorted(c[i] for c in edge)[len(edge) // 2] for i in range(3))
    canvas = Image.new("RGB", size, bg)
    canvas.paste(part, (px, py))
    canvas.save(dst)
    return max(0, px), max(0, py), min(size[0], px + part.width), min(size[1], py + part.height)


def pad_box(raw_size, size):
    """Where the resized GPT image sits inside the local tile size: (x0, y0, x1, y1)."""
    s = min(size[0] / raw_size[0], size[1] / raw_size[1])
    w, h = round(raw_size[0] * s), round(raw_size[1] * s)
    x0, y0 = (size[0] - w) // 2, (size[1] - h) // 2
    return x0, y0, x0 + w, y0 + h


def clean_pad(line_png, box, scale=2, margin=6):
    """Erase whatever the line extractor drew on the padding seam (lines are bright on black)."""
    im = Image.open(line_png).convert("L")
    x0, y0, x1, y1 = [v * scale for v in box]
    if (x0, y0) == (0, 0) and (x1, y1) == im.size:
        return
    m = margin * scale
    keep = Image.new("L", im.size, 0)
    keep.paste(im.crop((x0 + m, y0 + m, x1 - m, y1 - m)), (x0 + m, y0 + m))
    keep.save(line_png)


def normalise(src, size, dst):
    """Fit the GPT image into the local tile size, padding with its own background colour."""
    im = Image.open(src).convert("RGB")
    s = min(size[0] / im.width, size[1] / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    border = [im.getpixel((x, y)) for x in (0, im.width - 1) for y in range(0, im.height, 16)] + \
             [im.getpixel((x, y)) for y in (0, im.height - 1) for x in range(0, im.width, 16)]
    bg = tuple(sorted(c[i] for c in border)[len(border) // 2] for i in range(3))
    canvas = Image.new("RGB", size, bg)
    canvas.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    canvas.save(dst)


def extract(photo, base, kind, box=None):
    """photo -> base_line.png + base_sketch.png (and keypoints for bodies). Same extractors as the local run."""
    w, h = Image.open(photo).size
    tag = "gpt_" + re.sub(r"[^a-z0-9_]", "_", os.path.relpath(base, W).lower())
    with COMFY_LOCK:
        up = comfy.upload(photo)
        x = comfy.G()
        li = x.add("LoadImage", image=up)
        big = x.add("ImageScaleBy", image=[li, 0], upscale_method="lanczos", scale_by=2.0)
        if kind == "body":
            la = x.add("PiDiNetPreprocessor", image=[big, 0], safe="enable", resolution=min(w, h) * 2)
            op = x.add("OpenposePreprocessor", image=[li, 0], detect_hand="enable", detect_body="enable",
                       detect_face="disable", resolution=1024)
            x.add("SavePoseKpsAsJsonFile", pose_kps=[op, 1], filename_prefix=f"stencil2/{tag}_kps")
        else:
            la = x.add("TEEDPreprocessor", image=[big, 0], safe_steps=2, resolution=min(w, h) * 2)
        sv = x.add("SaveImage", images=[la, 0], filename_prefix=f"stencil2/{tag}_line")
        comfy.save_outputs(comfy.run(x.g), {sv: base + "_line.png"})
        kps = comfy.fetch_json("stencil2", f"{tag}_kps") if kind == "body" else None
    if box:
        clean_pad(base + "_line.png", box)
    to_sketch(base + "_line.png", base + "_sketch.png")
    if kps is not None:
        json.dump(kps, open(base + "_kps.json", "w"))
    return kps


def duo_check(kps):
    if not kps or not kps[0].get("people"):
        return False, ["no person detected"]
    real = [p for p in kps[0]["people"] if sum(1 for i in range(18) if p["pose_keypoints_2d"][3 * i + 2] > 0.3) >= 6]
    return (len(real) == 2), ([] if len(real) == 2 else [f"{len(real)} people detected"])


def body_tiles(stem, shape, prompt, ref, tries, check):
    """Generate up to `tries` times; return (base of the first passing try or None, reasons per try)."""
    size = (832, 1216) if shape == "portrait" else (1216, 832)
    why = []
    for t in range(1, tries + 1):
        raw = f"{stem}_t{t}.png"
        if not codex(raw, shape, prompt, ref):
            why.append("generation failed"); continue
        base = f"{stem}_t{t}"
        if not os.path.exists(base + "_kps.json"):
            box = fit_crop(raw, size, base + "_photo.png")
            extract(base + "_photo.png", base, "body", box)
        ok, reasons = check(json.load(open(base + "_kps.json")), size, shape)
        if ok:
            return base, why
        why.append("; ".join(reasons))
    return None, why


def place(base, dest, ok):
    """Copy a finished GPT try into its tile slot (dest_photo.png etc.) and mark it."""
    for suf in ("_photo.png", "_line.png", "_sketch.png", "_kps.json"):
        if os.path.exists(base + suf):
            shutil.copy2(base + suf, dest + suf)
    for m in ("_ok", "_flagged"):
        if os.path.exists(dest + m):
            os.remove(dest + m)
    open(dest + ("_ok" if ok else "_flagged"), "w").close()


# ---------- the three jobs ----------
def bodies_job(item):
    ci, char, desc, act, phrase, orient = item
    dest = os.path.join(W, "bodies", char, act)
    if not os.path.exists(dest + "_flagged"):
        return f"{char}/{act} already ok"
    ref = next((os.path.join(W, "bodies", char, a + "_photo.png") for a, _, _ in ACTIONS
                if os.path.exists(os.path.join(W, "bodies", char, a + "_ok"))), None)
    prompt = (f"full body photograph of the same person as in the attached photo ({desc}), same face, hair and clothes, "
              f"but in a new pose: {BODY_FIX.get(act, phrase)}, {FRAME[orient]}, {STUDIO}, {orient} aspect")
    check = lambda k, size, shape: body_check(k, *size, landscape=shape == "landscape", action=act)[:2]
    base, why = body_tiles(os.path.join(GPT, "bodies", char, act), orient, prompt, ref, 3, check)
    if base is None:
        return f"{char}/{act} kept local (GPT tries: {why})"
    keep = os.path.join(OLD, "bodies_local", char); os.makedirs(keep, exist_ok=True)
    for f in os.listdir(os.path.dirname(dest)):
        if f.startswith(act + "_"):
            shutil.copy2(os.path.join(os.path.dirname(dest), f), keep)
    place(base, dest, True)
    return f"{char}/{act} replaced by {os.path.basename(base)}"


def action_items(want):
    out = []
    for scene, phrase, orient, n in ACTION_SCENES:
        if want and scene not in want:
            continue
        for i, (slug, desc) in enumerate(ACTION_CAST):
            if n == 1:
                who, name = desc, slug
            else:
                j = (i + 1) % len(ACTION_CAST)
                who, name = f"{desc}, and {ACTION_CAST[j][1]}", f"{slug[0]}{ACTION_CAST[j][0][0]}_duo"
            out.append((scene, name, phrase, orient, n, who))
    return out


def actions_job(item):
    scene, name, phrase, orient, n, who = item
    dest = os.path.join(W, "actions", scene, name)
    if os.path.exists(dest + "_ok") or os.path.exists(dest + "_flagged"):
        return f"{scene}/{name} done"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if n == 1:
        prompt = f"full body action photograph of {who}, {phrase}, {FRAME[orient]}, dynamic but clear pose, {STUDIO}, {orient} aspect"
        check = lambda k, size, shape: body_check(k, *size, landscape=shape == "landscape")[:2]
    else:
        prompt = (f"full body action photograph of two people: {who}. {phrase}. Both bodies fully visible from head to feet "
                  f"and not overlapping much, with clear empty space around them, {STUDIO}, {orient} aspect")
        check = lambda k, size, shape: duo_check(k)
    base, why = body_tiles(os.path.join(GPT, "actions", scene, name), orient, prompt, None, 2, check)
    if base is None:
        last = max((b for b in (os.path.join(GPT, "actions", scene, f"{name}_t{t}") for t in (1, 2))
                    if os.path.exists(b + "_line.png")), default=None)
        if last is None:
            return f"{scene}/{name} FAILED ({why})"
        place(last, dest, False)
        return f"{scene}/{name} flagged ({why})"
    place(base, dest, True)
    return f"{scene}/{name} ok ({os.path.basename(base)})"


def face_job(item):
    pi, slug, desc, key, txt, kind = item
    stem = os.path.join(GPT, "faces", slug, key)
    if os.path.exists(stem + "_photo.png"):
        return f"{slug}/{key} skip"
    who = f"the same person as in the attached photo ({desc})"
    keepframe = "same framing, lighting, hair and clothes as the attached photo, close-up head and shoulders"
    if kind == "neutral":
        ref = os.path.join(W, "faces", slug, "01_neutral_photo.png")
        if os.path.exists(os.path.join(OLD, "faces_local", slug, "01_neutral_photo.png")):
            ref = os.path.join(OLD, "faces_local", slug, "01_neutral_photo.png")
        prompt = (f"close-up head and shoulders portrait photograph of {who}, neutral relaxed expression, looking straight into "
                  f"the camera, head straight, symmetrical front view, a little space above the hair, {STUDIO}")
    else:
        ref = os.path.join(GPT, "faces", slug, "01_neutral.png")
        if kind == "emotion":
            prompt = f"portrait photograph of {who}, {txt}, a strong clear facial expression, looking at the camera, {keepframe}, {STUDIO}"
        else:
            prompt = f"portrait photograph of {who}, neutral expression, {txt}, {keepframe}, {STUDIO}"
    if not os.path.exists(ref) or not codex(stem + ".png", "square", prompt, ref):
        return f"{slug}/{key} FAILED"
    normalise(stem + ".png", (1024, 1024), stem + "_photo.png")
    return f"{slug}/{key} ok"


def swap_faces(slug):
    """Back up the local person once, then put every finished GPT tile in its place."""
    src, dst, keep = os.path.join(GPT, "faces", slug), os.path.join(W, "faces", slug), os.path.join(OLD, "faces_local", slug)
    if not os.path.exists(keep):
        shutil.copytree(dst, keep)
    n = 0
    for key, _ in EMOTIONS + ANGLES:
        if os.path.exists(os.path.join(src, key + "_photo.png")):
            shutil.copy2(os.path.join(src, key + "_photo.png"), os.path.join(dst, key + "_photo.png"))
            n += 1
    return n


def reclean():
    """Clean the padding seam on body/action tiles made before clean_pad existed, and refresh their placed copies."""
    import glob, hashlib
    h = lambda f: hashlib.md5(open(f, "rb").read()).hexdigest()
    placed = {}
    for f in glob.glob(os.path.join(W, "bodies", "*", "*_line.png")) + glob.glob(os.path.join(W, "actions", "*", "*_line.png")):
        placed.setdefault(h(f), []).append(f[:-len("_line.png")])
    n = 0
    for line in glob.glob(os.path.join(GPT, "bodies", "*", "*_t?_line.png")) + glob.glob(os.path.join(GPT, "actions", "*", "*_t?_line.png")):
        base = line[:-len("_line.png")]
        raw = Image.open(base + ".png")
        size = (832, 1216) if raw.width < raw.height else (1216, 832)
        before = h(line)
        clean_pad(line, pad_box(raw.size, size)); to_sketch(line, base + "_sketch.png")
        for dest in placed.get(before, []):
            shutil.copy2(line, dest + "_line.png"); shutil.copy2(base + "_sketch.png", dest + "_sketch.png")
            n += 1
    print("re-cleaned, placed copies refreshed:", n)


def refit():
    """Redo every body/action try from its raw GPT image with fit_crop, re-check, and re-place. No Codex calls."""
    import glob
    orient = {a: o for a, _, o in ACTIONS}
    scenes = {sc: (o, n) for sc, _, o, n in ACTION_SCENES}
    stems = {}
    for raw in glob.glob(os.path.join(GPT, "bodies", "*", "*_t?.png")) + glob.glob(os.path.join(GPT, "actions", "*", "*_t?.png")):
        stems.setdefault(raw[:-7], []).append(raw)
    for stem, raws in sorted(stems.items()):
        group, name = os.path.basename(os.path.dirname(os.path.dirname(stem))), os.path.basename(stem)
        sub = os.path.basename(os.path.dirname(stem))
        if group == "bodies":
            shape = orient[name]
            check = lambda k, size, shape=shape, act=name: body_check(k, *size, landscape=shape == "landscape", action=act)[:2]
        else:
            shape, n = scenes[sub]
            check = (lambda k, size, shape=shape: body_check(k, *size, landscape=shape == "landscape")[:2]) if n == 1 else \
                    (lambda k, size: duo_check(k))
        size = (832, 1216) if shape == "portrait" else (1216, 832)
        win, last, why = None, None, []
        for raw in sorted(raws):
            base = raw[:-4]
            extract(base + "_photo.png", base, "body", fit_crop(raw, size, base + "_photo.png"))
            ok, reasons = check(json.load(open(base + "_kps.json")), size)
            last = base
            if ok:
                win = base; break
            why.append("; ".join(reasons))
        dest = os.path.join(W, group, sub, name)
        if group == "bodies":
            keep = os.path.join(OLD, "bodies_local", sub)
            if win:
                if not os.path.exists(os.path.join(keep, name + "_line.png")):
                    os.makedirs(keep, exist_ok=True)
                    for f in os.listdir(os.path.dirname(dest)):
                        if f.startswith(name + "_"):
                            shutil.copy2(os.path.join(os.path.dirname(dest), f), keep)
                place(win, dest, True)
            print(sub, name, "GPT" if win else "local (still flagged)", why, flush=True)
        else:
            place(win or last, dest, bool(win))
            print(sub, name, "ok" if win else f"flagged {why}", flush=True)


def placed_raw(dest, stem):
    """Which GPT try a placed tile came from (matched by photo bytes), else None."""
    import glob, hashlib
    if not os.path.exists(dest + "_photo.png"):
        return None
    h = lambda f: hashlib.md5(open(f, "rb").read()).hexdigest()
    want = h(dest + "_photo.png")
    for raw in sorted(glob.glob(stem + "_t?.png")):
        if os.path.exists(raw[:-4] + "_photo.png") and h(raw[:-4] + "_photo.png") == want:
            return raw
    return None


def photo_action(item):
    """Photos-only mode: one GPT image per tile, framed on the figure; no tracing, check or retry."""
    scene, name, phrase, orient, n, who = item
    dest, stem = os.path.join(W, "actions", scene, name), os.path.join(GPT, "actions", scene, name)
    size = (832, 1216) if orient == "portrait" else (1216, 832)
    raw = placed_raw(dest, stem) or next(iter(sorted(__import__("glob").glob(stem + "_t?.png"))), None)
    if raw is None:
        if n == 1:
            prompt = f"full body action photograph of {who}, {phrase}, {FRAME[orient]}, dynamic but clear pose, {STUDIO}, {orient} aspect"
        else:
            prompt = (f"full body action photograph of two people: {who}. {phrase}. Both bodies fully visible from head to feet "
                      f"and not overlapping much, with clear empty space around them, {STUDIO}, {orient} aspect")
        raw = stem + "_t1.png"
        if not codex(raw, orient, prompt):
            return f"{scene}/{name} FAILED"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    fit_crop(raw, size, dest + "_photo.png")
    if not os.path.exists(dest + "_flagged"):
        open(dest + "_ok", "w").close()
    return f"{scene}/{name} photo from {os.path.basename(raw)}"


def photo_bodies():
    """Reframe the GPT bodies already placed (they were padded) with fit_crop."""
    n = 0
    for char, _ in CHARACTERS:
        for act, _, orient in ACTIONS:
            dest, stem = os.path.join(W, "bodies", char, act), os.path.join(GPT, "bodies", char, act)
            raw = placed_raw(dest, stem)
            if raw:
                fit_crop(raw, (832, 1216) if orient == "portrait" else (1216, 832), dest + "_photo.png"); n += 1
    print("GPT body photos reframed:", n)


def pool(fn, items):
    with ThreadPoolExecutor(PAR) as ex:
        for r in ex.map(fn, items):
            print(r, flush=True)


if __name__ == "__main__":
    os.makedirs(GPT, exist_ok=True)
    what, want = sys.argv[1], set(sys.argv[2:])
    if what == "photos":
        photo_bodies()
        pool(photo_action, action_items(want))
    elif what == "refit":
        refit()
    elif what == "reclean":
        reclean()
    elif what == "bodies":
        pool(bodies_job, [(ci, c, d, a, p, o) for ci, (c, d) in enumerate(CHARACTERS) for a, p, o in ACTIONS
                          if (not want or c in want) and os.path.exists(os.path.join(W, "bodies", c, a + "_flagged"))])
    elif what == "actions":
        pool(actions_job, action_items(want))
    elif what == "faces":
        people = [(pi, s, d) for pi, (s, d) in enumerate(PEOPLE) if not want or s in want]
        pool(face_job, [(pi, s, d, "01_neutral", "", "neutral") for pi, s, d in people])
        # person by person, so a quota stop leaves whole people done rather than every person half GPT, half local
        rest = [it for pi, s, d in people for it in
                [(pi, s, d, k, t, "emotion") for k, t in EMOTIONS[1:]] + [(pi, s, d, k, t, "angle") for k, t in ANGLES]]
        pool(face_job, rest)
        for pi, s, d in people:
            print(s, "GPT tiles in place:", swap_faces(s), flush=True)
    if abort.is_set():
        sys.exit(2)
