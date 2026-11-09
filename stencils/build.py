"""Assemble the stencil tiles into Krita-ready OpenRaster files.

usage: python3 stencils/build.py            -> out/bodies.ora, out/faces.ora, out/*_contact.png
Flagged body tiles are still included, with "(check)" in the layer name, so nothing silently vanishes.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw
from ora import write_ora
from sketch import to_layer
from specs import ACTION_SCENES, ACTIONS, FILM_A, FILM_B, FILM_C, FILM_DUOS, ANGLES, CHARACTERS, EMOTIONS, PEOPLE

HERE = os.path.dirname(os.path.abspath(__file__))
WORK, OUT = os.path.join(HERE, "..", "work"), os.path.join(HERE, "..", "out")


def photo_layer(path):
    return Image.open(path).convert("RGBA")


def label(slug):
    return slug.split("_", 1)[1].replace("_", " ")


def bodies():
    groups, contact, missing = [], [], []
    for char, _ in CHARACTERS:
        layers = []
        for act, _, _ in ACTIONS:
            base = os.path.join(WORK, "bodies", char, act)
            if not os.path.exists(base + "_photo.png"):
                missing.append(f"{char}/{act}"); continue
            name = f"{char[:2]} {label(act)}" + ("" if os.path.exists(base + "_ok") else " (check)")
            layers.append((name, photo_layer(base + "_photo.png")))
            contact.append((base + "_photo.png", name))
        if layers:
            groups.append((f"{char[:2]} {label(char)}", layers))
    n = write_ora(os.path.join(OUT, "bodies.ora"), (1216, 1216), groups)
    sheet(contact, os.path.join(OUT, "bodies_contact.png"), cols=10, cell=(200, 290))
    return n, missing


def faces():
    groups, contact, missing = [], [], []
    for slug, _ in PEOPLE:
        sub = []
        for title, items in (("emotions", EMOTIONS), ("angles", ANGLES)):
            layers = []
            for s, _ in items:
                base = os.path.join(WORK, "faces", slug, s)
                if not os.path.exists(base + "_photo.png"):
                    missing.append(f"{slug}/{s}"); continue
                name = f"{slug[:2]} {label(s)}"
                layers.append((name, photo_layer(base + "_photo.png")))
                contact.append((base + "_photo.png", name))
            if layers:
                sub.append((title, layers))
        if sub:
            groups.append((f"{slug[:2]} {label(slug)}", sub))
    n = write_ora(os.path.join(OUT, "faces.ora"), (1024, 1024), groups)
    sheet(contact, os.path.join(OUT, "faces_contact.png"), cols=18, cell=(160, 160))
    return n, missing


def actions(folder="actions", scenes=None, out="actions"):
    """One group per scene (sprint, aim, grenade...), one layer per character or pair."""
    groups, contact, missing = [], [], []
    for scene in scenes or [s for s, _, _, _ in ACTION_SCENES]:
        d = os.path.join(WORK, folder, scene)
        names = sorted({f[:-len("_photo.png")] for f in os.listdir(d) if f.endswith("_photo.png") and not re.search(r"_t\d_photo", f)}) if os.path.isdir(d) else []
        if not names:
            missing.append(scene); continue
        layers = []
        for n in names:
            base = os.path.join(d, n)
            name = f"{scene[:2]} {n.replace('_', ' ')}" + ("" if os.path.exists(base + "_ok") else " (check)")
            layers.append((name, photo_layer(base + "_photo.png")))
            contact.append((base + "_photo.png", f"{label(scene)} {name[3:]}"))
        groups.append((f"{scene[:2]} {label(scene)}", layers))
    n = write_ora(os.path.join(OUT, f"{out}.ora"), (1216, 1216), groups)
    sheet(contact, os.path.join(OUT, f"{out}_contact.png"), cols=10, cell=(220, 290))
    return n, missing


def film():
    return actions("film", [s for s, _ in FILM_A + FILM_B + FILM_C + FILM_DUOS], "film")


def sheet(items, path, cols, cell):
    if not items:
        return
    rows = (len(items) + cols - 1) // cols
    s = Image.new("RGB", (cols * cell[0], rows * (cell[1] + 16)), "white"); d = ImageDraw.Draw(s)
    for i, (p, name) in enumerate(items):
        im = Image.open(p).convert("RGB"); im.thumbnail(cell)
        x, y = (i % cols) * cell[0], (i // cols) * (cell[1] + 16)
        s.paste(im, (x + (cell[0] - im.width) // 2, y + 16)); d.text((x + 3, y + 2), name, fill="black")
    s.save(path)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    what = sys.argv[1:] or ["bodies", "faces", "actions", "film"]
    for w in what:
        n, missing = {"bodies": bodies, "faces": faces, "actions": actions, "film": film}[w]()
        size = os.path.getsize(os.path.join(OUT, f"{w}.ora")) / 1e6
        print(f"{w}.ora: {n} layers incl. paper and draw-here, {size:.0f} MB, missing {len(missing)}: {missing[:8]}")
