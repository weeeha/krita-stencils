"""Write OpenRaster (.ora) files that Krita opens with groups and layers intact.

Layout, top to bottom:
    draw here         empty, visible, the layer to draw on
    <group per person> visible; stencil layers inside, all hidden except the very first one
    paper             white, visible
Stencil layers are black ink with alpha (see sketch.to_layer), so they read as grey 110 over the paper.
"""
import io, os, zipfile
from xml.sax.saxutils import quoteattr
from PIL import Image


def _png(im):
    b = io.BytesIO(); im.save(b, "PNG", optimize=True); return b.getvalue()


def write_ora(path, size, groups, first_visible=True):
    """groups: [(group_name, [(layer_name, PIL.Image RGBA)] or [(subgroup_name, [...])])]

    Each layer image is centred on the canvas.
    """
    W, H = size
    files, n = {}, [0]

    def layer_xml(name, im, visible):
        n[0] += 1
        src = f"data/{n[0]:04d}.png"
        files[src] = _png(im)
        x, y = (W - im.width) // 2, (H - im.height) // 2
        return (f'<layer name={quoteattr(name)} src="{src}" x="{x}" y="{y}" opacity="1.0" '
                f'visibility="{"visible" if visible else "hidden"}" composite-op="svg:src-over"/>')

    shown = [not first_visible]  # flips to True once one stencil is visible

    def walk(items):
        out = []
        for name, content in items:
            if isinstance(content, list):
                out.append(f'<stack name={quoteattr(name)} visibility="visible">{"".join(walk(content))}</stack>')
            else:
                vis = not shown[0]
                shown[0] = True
                out.append(layer_xml(name, content, vis))
        return out

    body = []
    body.append(layer_xml("draw here", Image.new("RGBA", (W, H), (0, 0, 0, 0)), True))
    body += walk(groups)
    paper = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    body.append(layer_xml("paper", paper, True))
    stack = (f'<?xml version="1.0" encoding="UTF-8"?>\n<image version="0.0.3" w="{W}" h="{H}" xres="300" yres="300">'
             f'<stack>{"".join(body)}</stack></image>')

    # merged preview = paper + the one visible stencil
    merged = paper.copy()
    first = _first_layer(groups)
    if first is not None:
        merged.alpha_composite(first, ((W - first.width) // 2, (H - first.height) // 2))
    thumb = merged.copy(); thumb.thumbnail((256, 256))

    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "image/openraster", compress_type=zipfile.ZIP_STORED)
        z.writestr("stack.xml", stack, compress_type=zipfile.ZIP_DEFLATED)
        for src, data in files.items():
            z.writestr(src, data, compress_type=zipfile.ZIP_STORED)  # PNG is already compressed
        z.writestr("mergedimage.png", _png(merged.convert("RGB")), compress_type=zipfile.ZIP_STORED)
        z.writestr("Thumbnails/thumbnail.png", _png(thumb.convert("RGB")), compress_type=zipfile.ZIP_STORED)
    os.replace(tmp, path)
    return n[0]


def _first_layer(items):
    for _, c in items:
        if isinstance(c, list):
            r = _first_layer(c)
            if r is not None:
                return r
        else:
            return c
    return None
