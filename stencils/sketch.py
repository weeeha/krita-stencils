"""Turn line-art output (white lines on black) into stencils.

Darkness: Nick picked level 2, a full line reads as grey 110 on white.
"""
from PIL import Image, ImageOps

LINE_GREY = 110


def to_sketch(line_png, out_png, grey=LINE_GREY):
    """Opaque preview: grey lines on white."""
    im = Image.open(line_png).convert("L")
    lut = [255 - int(p * (255 - grey) / 255) for p in range(256)]
    im.point(lut).save(out_png)


def to_layer(line_png, grey=LINE_GREY):
    """Transparent layer: black ink whose alpha makes a full line read as `grey` over white paper."""
    im = Image.open(line_png).convert("L")
    alpha = im.point([int(p * (255 - grey) / 255) for p in range(256)])
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    layer.putalpha(alpha)
    return layer
