"""Draw OpenPose-format skeletons with 8-head proportions for ControlNet.

Keypoints are authored in head units: x to the right, y down, 0 = top of head,
8 = sole of the feet. Canvas 832x1216 (SDXL portrait); figure scaled to 7.6 of
the 8 heads fitting the height with margin.
OpenPose 18-point order (controlnet_aux colours): nose, neck, Rsho, Relb, Rwri,
Lsho, Lelb, Lwri, Rhip, Rknee, Rank, Lhip, Lknee, Lank, Reye, Leye, Rear, Lear.
"Right" is the figure's right, which is on the viewer's left in a front view.
"""
import json, sys
from PIL import Image, ImageDraw

W, H = 832, 1216
LIMBS = [(1,2),(1,5),(2,3),(3,4),(5,6),(6,7),(1,8),(8,9),(9,10),(1,11),(11,12),(12,13),(1,0),(0,14),(14,16),(0,15),(15,17)]
COLORS = [(255,0,0),(255,85,0),(255,170,0),(255,255,0),(170,255,0),(85,255,0),(0,255,0),(0,255,85),(0,255,170),(0,255,255),(0,170,255),(0,85,255),(0,0,255),(85,0,255),(170,0,255),(255,0,255),(255,0,170),(255,0,85)]

def head(x, y, yaw=0.0):
    """Face keypoints around a head whose nose is at (x, y). yaw: -1 profile right ... 1 profile left."""
    return {0:(x,y), 14:(x-0.12*(1-max(yaw,0)), y-0.12), 15:(x+0.12*(1-max(-yaw,0)), y-0.12), 16:(x-0.33, y-0.08) if yaw<0.8 else None, 17:(x+0.33, y-0.08) if yaw>-0.8 else None}

# Front standing, 8 heads: nose 0.55, neck 1.2, shoulders 1.55, elbow 3.0, wrist 4.3, hips 4.0, knee 6.0, ankle 7.7
def pose_standing():
    p = head(0, 0.55)
    p.update({1:(0,1.2), 2:(-0.9,1.55), 3:(-1.0,3.0), 4:(-1.05,4.3), 5:(0.9,1.55), 6:(1.0,3.0), 7:(1.05,4.3),
              8:(-0.5,4.0), 9:(-0.5,6.0), 10:(-0.5,7.7), 11:(0.5,4.0), 12:(0.5,6.0), 13:(0.5,7.7)})
    return p

def pose_walking():  # three-quarter view, right leg forward, left arm forward
    p = head(0.1, 0.55, yaw=-0.3)
    p.update({1:(0.05,1.2), 2:(-0.7,1.55), 3:(-0.95,2.9), 4:(-0.75,4.1), 5:(0.75,1.55), 6:(0.55,2.9), 7:(0.05,3.9),
              8:(-0.45,4.0), 9:(-0.85,5.9), 10:(-0.95,7.6), 11:(0.4,4.0), 12:(0.8,5.9), 13:(1.3,7.6)})
    return p

def pose_running():  # side-ish view, strong stride, lean forward
    p = head(0.35, 0.65, yaw=-0.7)
    p.update({1:(0.2,1.3), 2:(0.0,1.6), 3:(-0.5,2.7), 4:(0.3,3.3), 5:(0.4,1.6), 6:(1.1,2.5), 7:(1.3,1.7),
              8:(-0.2,4.0), 9:(-1.2,5.3), 10:(-1.3,7.0), 11:(0.1,4.0), 12:(0.9,5.6), 13:(1.6,7.3)})
    return p

def pose_sitting():  # on a stool, three-quarter, hands on knees
    p = head(0, 0.55, yaw=0.2)
    p.update({1:(0,1.2), 2:(-0.9,1.55), 3:(-1.05,3.0), 4:(-0.85,4.25), 5:(0.9,1.55), 6:(1.05,3.0), 7:(0.95,4.25),
              8:(-0.5,4.0), 9:(-0.8,4.2), 10:(-0.9,6.1), 11:(0.5,4.0), 12:(0.95,4.2), 13:(1.05,6.1)})
    return p

def pose_reaching():  # front, right arm straight up, weight on left leg
    p = head(0.05, 0.6)
    p.update({1:(0,1.25), 2:(-0.85,1.5), 3:(-1.05,0.4), 4:(-0.95,-0.9), 5:(0.9,1.6), 6:(1.05,3.0), 7:(1.0,4.3),
              8:(-0.45,4.0), 9:(-0.55,6.0), 10:(-0.35,7.7), 11:(0.55,4.0), 12:(0.7,6.0), 13:(0.85,7.7)})
    return p

POSES = {"standing": pose_standing, "walking": pose_walking, "running": pose_running, "sitting": pose_sitting, "reaching": pose_reaching}

def render(name, out_png, out_json):
    pts = POSES[name]()
    ys = [v[1] for v in pts.values() if v]
    top, bot = min(ys) - 0.55, max(ys) + 0.3   # crown above nose, foot below ankle
    scale = (H * 0.92) / (bot - top)
    scale = min(scale, H * 0.92 / 8.0)        # never bigger than 8 heads in 92% of height
    oy = (H - (bot - top) * scale) / 2 - top * scale
    def P(v):
        return (W / 2 + v[0] * scale, oy + v[1] * scale)
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    r = max(4, int(scale * 0.06))
    for i, (a, b) in enumerate(LIMBS):
        if pts.get(a) and pts.get(b):
            d.line([P(pts[a]), P(pts[b])], fill=COLORS[i], width=r)
    for k, v in pts.items():
        if v:
            x, y = P(v); d.ellipse([x - r, y - r, x + r, y + r], fill=COLORS[k])
    img.save(out_png)
    json.dump({k: P(v) for k, v in pts.items() if v}, open(out_json, "w"))
    return scale

if __name__ == "__main__":
    out = sys.argv[1]
    for n in POSES:
        s = render(n, f"{out}/pose_{n}.png", f"{out}/pose_{n}.json")
        print(n, "head px", round(s))
