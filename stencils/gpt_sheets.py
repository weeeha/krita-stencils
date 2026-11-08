"""Character sheets: many poses or faces in one GPT (Codex) image, then cut into separate tiles.

python3 stencils/gpt_sheets.py test      one action sheet + one face sheet
python3 stencils/gpt_sheets.py film      two 12-pose sheets per film character (6x2): getting by, running away
python3 stencils/gpt_sheets.py duos      6-scene two-person sheet per pair (3x2)
python3 stencils/gpt_sheets.py faces     two sheets per person: 10 emotions + 2 angles (4x3), 6 angles (3x2)
python3 stencils/gpt_sheets.py split     cut every sheet at its white gutters, upscale cells on ArtPC (4x NMKD), place tiles
Sheets are kept in work/sheets/; a rerun skips finished sheets.
"""
import json, os, sys, shutil
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
import comfy
from gpt_upgrade import codex, fit_crop, normalise, STUDIO, abort, COMFY_LOCK
from specs import ANGLES, EMOTIONS, FILM_A, FILM_B, FILM_C, FILM_CAST, FILM_DUOS, FILM_LANDSCAPE, PEOPLE

HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.normpath(os.path.join(HERE, "..", "work"))
SH, OLD = os.path.join(W, "sheets"), os.path.join(W, "_old")
FACE_A = EMOTIONS + ANGLES[:2]   # 12 cells
FACE_B = ANGLES[2:]              # 6 cells


def grid_prompt(cols, rows, who, cells, framing):
    listing = " ".join(f"{i + 1}) {c}." for i, c in enumerate(cells))
    return (f"A reference sheet photograph laid out as a precise grid of {cols} columns and {rows} rows of equal-size cells, "
            f"separated by thin pure white gutters, with a thin pure white border. Every cell shows {who}, {framing}, "
            f"on a plain light grey studio background with soft even lighting. Cells from left to right, top to bottom: {listing} "
            f"Realistic photo, correct human anatomy and proportions, nothing crosses the gutters, no text, no numbers, no labels.")


def jobs(kind):
    out = []
    if kind in ("film", "test"):
        for slug, desc in FILM_CAST[: 1 if kind == "test" else None]:
            for part, scenes in (("A", FILM_A), ("B", FILM_B))[: 1 if kind == "test" else None]:
                out.append((f"film/{slug}_{part}", "landscape", 6, 2,
                            grid_prompt(6, 2, f"the same person: {desc}", [p for _, p in scenes],
                                        "full body visible from head to feet with a little space around it"), None))
            if kind == "film":
                out.append((f"film/{slug}_C", "landscape", 4, 3,
                            grid_prompt(4, 3, f"the same stunt performer: {desc}", [p for _, p in FILM_C],
                                        "film stunt still, full body visible, no blood, no injuries, no gore"), None))
    if kind == "duos":
        for i, (slug, desc) in enumerate(FILM_CAST):
            j = (i + 1) % len(FILM_CAST)
            who = f"the same two people: person one is {desc}; person two is {FILM_CAST[j][1]}"
            out.append((f"duos/{slug[0]}{FILM_CAST[j][0][0]}", "landscape", 3, 2,
                        grid_prompt(3, 2, who, [p for _, p in FILM_DUOS], "both bodies fully visible from head to feet"), None))
    if kind in ("faces", "test"):
        for slug, desc in PEOPLE[1:2] if kind == "test" else PEOPLE:
            ref = os.path.join(OLD, "faces_local", slug, "01_neutral_photo.png")
            if not os.path.exists(ref):
                ref = os.path.join(W, "faces", slug, "01_neutral_photo.png")
            who = f"the same person as in the attached photo ({desc}), same face, hair and clothes"
            frame = "a close-up head and shoulders portrait, head centred in the cell"
            out.append((f"faces/{slug}_A", "square", 4, 3, grid_prompt(4, 3, who, [t for _, t in FACE_A], frame), ref))
            if kind == "faces":
                out.append((f"faces/{slug}_B", "square", 3, 2,
                            grid_prompt(3, 2, who, [f"neutral expression, {t}" for _, t in FACE_B], frame), ref))
    return out


def make(job):
    name, shape, cols, rows, prompt, ref = job
    out = os.path.join(SH, name + ".png")
    ok = codex(out, shape, prompt, ref)
    if ok:
        json.dump({"cols": cols, "rows": rows}, open(out[:-4] + ".json", "w"))
    return f"{name} {'ok' if ok else 'FAILED'}"


# ---------- splitting ----------
def cuts(white_frac, n, size):
    """n-1 split positions: the whitest line near each expected boundary."""
    pos = []
    for k in range(1, n):
        c = round(k * size / n); r = round(0.08 * size / n * 2)
        lo, hi = max(1, c - r), min(size - 1, c + r)
        seg = white_frac[lo:hi]
        best = seg.max()
        idx = np.where(seg >= best - 0.01)[0]
        pos.append((lo + int(np.median(idx)), float(best)))
    return pos


def trim(cell):
    """Drop white gutter edges around a cell."""
    a = np.asarray(cell.convert("RGB")).min(2) > 235
    rows, cols = np.where(a.mean(1) < 0.9)[0], np.where(a.mean(0) < 0.9)[0]
    if len(rows) == 0 or len(cols) == 0:
        return cell
    return cell.crop((int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1))


def split(path):
    meta = json.load(open(path[:-4] + ".json"))
    im = Image.open(path).convert("RGB")
    white = np.asarray(im).min(2) > 235
    xs = cuts(white.mean(0), meta["cols"], im.width)
    ys = cuts(white.mean(1), meta["rows"], im.height)
    clean = min([q for _, q in xs + ys] or [1]) > 0.9
    bx = [0] + [p for p, _ in xs] + [im.width]
    by = [0] + [p for p, _ in ys] + [im.height]
    cells = []
    for r in range(meta["rows"]):
        for c in range(meta["cols"]):
            cells.append(trim(im.crop((bx[c], by[r], bx[c + 1], by[r + 1]))))
    return cells, clean


def upscale(cell, dst):
    tmp = dst[:-4] + "_cell.png"
    cell.save(tmp)
    with COMFY_LOCK:
        x = comfy.G()
        li = x.add("LoadImage", image=comfy.upload(tmp))
        m = x.add("UpscaleModelLoader", model_name="4x_NMKD-Superscale-SP_178000_G.pth")
        up = x.add("ImageUpscaleWithModel", upscale_model=[m, 0], image=[li, 0])
        sv = x.add("SaveImage", images=[up, 0], filename_prefix="stencil2/sheetcell")
        comfy.save_outputs(comfy.run(x.g), {sv: dst})
    os.remove(tmp)


def place_tile(dest, src_big, size, body, clean):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if body:
        fit_crop(src_big, size, dest + "_photo.png")
    else:
        normalise(src_big, size, dest + "_photo.png")
    for m in ("_ok", "_flagged"):
        if os.path.exists(dest + m):
            os.remove(dest + m)
    open(dest + ("_ok" if clean else "_flagged"), "w").close()


def split_all():
    import glob
    tmpdir = os.path.join(SH, "_cells"); os.makedirs(tmpdir, exist_ok=True)
    for path in sorted(glob.glob(os.path.join(SH, "*", "*.png"))):
        kind, name = path.split(os.sep)[-2], os.path.basename(path)[:-4]
        if kind == "_cells" or not os.path.exists(path[:-4] + ".json"):
            continue
        done = path[:-4] + ".placed"
        if os.path.exists(done):
            continue
        cells, clean = split(path)
        if kind == "film":
            slug, part = name.rsplit("_", 1)
            targets = [(os.path.join(W, "film", s, slug), True) for s, _ in {"A": FILM_A, "B": FILM_B, "C": FILM_C}[part]]
        elif kind == "duos":
            targets = [(os.path.join(W, "film", s, name + "_duo"), True) for s, _ in FILM_DUOS]
        else:
            slug, part = name.rsplit("_", 1)
            keys = FACE_A if part == "A" else FACE_B
            keep = os.path.join(OLD, "faces_local", slug)
            if not os.path.exists(keep):
                shutil.copytree(os.path.join(W, "faces", slug), keep)
            targets = [(os.path.join(W, "faces", slug, k), False) for k, _ in keys]
        for (dest, body), cell in zip(targets, cells):
            big = os.path.join(tmpdir, f"{kind}_{name}_{os.path.basename(dest)}.png")
            if not os.path.exists(big):
                upscale(cell, big)
            orient = "landscape" if body and os.path.basename(os.path.dirname(dest)) in FILM_LANDSCAPE else "portrait"
            size = (1024, 1024) if not body else ((1216, 832) if orient == "landscape" or kind == "duos" else (832, 1216))
            place_tile(dest, big, size, body, clean)
        open(done, "w").close()
        print(name, kind, "placed", len(targets), "clean" if clean else "UNCLEAN gutters", flush=True)


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "split":
        split_all()
    else:
        with ThreadPoolExecutor(4) as ex:
            for r in ex.map(make, jobs(what)):
                print(r, flush=True)
        if abort.is_set():
            sys.exit(2)
