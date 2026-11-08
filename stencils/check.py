"""Automatic body check on OpenPose keypoints detected from the finished photo.

Catches what wrecks a tracing stencil: two people, missing or cut-off limbs,
a figure too small to trace, and grossly wrong limb lengths. Hands and faces
are not checked here; those go through a human look at the contact sheets.
"""
import math

NOSE, NECK, RSHO, RELB, RWRI, LSHO, LELB, LWRI, RHIP, RKNE, RANK, LHIP, LKNE, LANK = range(14)
CORE = [NECK, RSHO, LSHO, RHIP, LHIP, RKNE, LKNE, RANK, LANK]
ARMS = [RELB, RWRI, LELB, LWRI]


def body_check(kps, w, h, landscape=False, action=None):
    """Return (ok, reasons, metrics). kps: SavePoseKpsAsJsonFile output (normalised coords)."""
    reasons = []
    if not kps or not kps[0].get("people"):
        return False, ["no person detected"], {}
    people = kps[0]["people"]
    real = [p for p in people if sum(1 for i in range(18) if p["pose_keypoints_2d"][3 * i + 2] > 0.3) >= 6]
    if len(real) != 1:
        reasons.append(f"{len(real)} people detected")
    p = (real or people)[0]["pose_keypoints_2d"]
    pt = {i: (p[3 * i] * w, p[3 * i + 1] * h) for i in range(18) if p[3 * i + 2] > 0.3}

    missing_core = [i for i in CORE if i not in pt]
    if missing_core:
        reasons.append(f"core joints missing {missing_core}")
    if sum(1 for i in ARMS if i not in pt) > 2:
        reasons.append("arms mostly missing")

    xs = [v[0] for v in pt.values()]; ys = [v[1] for v in pt.values()]
    if xs and (min(xs) < 0.02 * w or max(xs) > 0.98 * w):
        reasons.append("touches side edge")
    for a in (RANK, LANK):
        if a in pt and pt[a][1] > 0.94 * h:
            reasons.append("feet cut at the bottom")
            break
    top = min(ys) if ys else 0
    if top < 0.07 * h:
        reasons.append("head near top edge")

    span = max(max(xs) - min(xs), max(ys) - min(ys)) if xs else 0
    long_side = w if landscape else h
    if span < 0.5 * long_side:
        reasons.append(f"figure small ({span / long_side:.0%} of frame)")

    def d(a, b):
        return math.dist(pt[a], pt[b]) if a in pt and b in pt else None

    m = {}
    for side, (hip, kne, ank, sho, elb, wri) in {"R": (RHIP, RKNE, RANK, RSHO, RELB, RWRI), "L": (LHIP, LKNE, LANK, LSHO, LELB, LWRI)}.items():
        th, sh = d(hip, kne), d(kne, ank)
        if th and sh:
            m[f"{side}_thigh_shin"] = round(th / sh, 2)
            if not 0.5 <= th / sh <= 2.0:
                reasons.append(f"{side} thigh/shin {th / sh:.2f}")
        ua, fa = d(sho, elb), d(elb, wri)
        if ua and fa:
            m[f"{side}_upper_fore"] = round(ua / fa, 2)
            if not 0.45 <= ua / fa <= 2.2:
                reasons.append(f"{side} upper arm/forearm {ua / fa:.2f}")
    lr, ll = d(RHIP, RKNE), d(LHIP, LKNE)
    tr = d(RSHO, RHIP) or d(NECK, RHIP)
    if tr and lr and ll:
        leg = (lr + ll) / 2 + ((d(RKNE, RANK) or 0) + (d(LKNE, LANK) or 0)) / 2
        m["leg_torso"] = round(leg / tr, 2)
        if leg / tr < 0.9:
            reasons.append(f"legs short for torso ({leg / tr:.2f})")
    m["span"] = round(span / long_side, 2)
    if action and pt:
        bad = action_problem(action, pt)
        if bad:
            reasons.append(bad)
    return not reasons, reasons, m


def angle(a, b, c):
    """Angle at b in degrees."""
    v1, v2 = (a[0] - b[0], a[1] - b[1]), (c[0] - b[0], c[1] - b[1])
    n = math.hypot(*v1) * math.hypot(*v2)
    return 180.0 if n == 0 else math.degrees(math.acos(max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / n))))


def action_problem(action, pt):
    """Does the pose actually show the action? Returns a reason string, or None when it does."""
    def y(i): return pt[i][1] if i in pt else None
    def x(i): return pt[i][0] if i in pt else None
    hips = [y(i) for i in (RHIP, LHIP) if i in pt]
    hip_y = sum(hips) / len(hips) if hips else None
    torso = math.dist(pt[NECK], ((pt[RHIP][0] + pt[LHIP][0]) / 2, hip_y)) if NECK in pt and RHIP in pt and LHIP in pt else None
    if not torso:
        return "cannot measure the action"
    a = action.split("_", 1)[1]
    wr = [i for i in (RWRI, LWRI) if i in pt]
    if a == "reaching":
        top = y(NOSE if NOSE in pt else NECK)
        ok = any(wri in pt and elb in pt and sho in pt and y(wri) < top - 0.3 * torso and y(elb) < y(sho)
                 for sho, elb, wri in ((RSHO, RELB, RWRI), (LSHO, LELB, LWRI)))
        if not ok:
            return "reaching: no arm stretched up above the head"
    elif a == "pointing":
        ok = False
        for sho, wri in ((RSHO, RWRI), (LSHO, LWRI)):
            if sho in pt and wri in pt and abs(y(wri) - y(sho)) < 0.35 * torso and abs(x(wri) - x(sho)) > 0.6 * torso:
                ok = True
        if not ok:
            return "pointing: no arm held out at shoulder height"
    elif a == "lying":
        if abs(y(NECK) - hip_y) > 0.45 * torso:
            return "lying: torso is not horizontal"
    elif a == "sitting":
        kn = [y(i) for i in (RKNE, LKNE) if i in pt]
        if not kn or min(abs(k - hip_y) for k in kn) > 0.45 * torso:
            return "sitting: thighs are not roughly level"
    elif a == "crouching":
        kn = [y(i) for i in (RKNE, LKNE) if i in pt]
        an = [y(i) for i in (RANK, LANK) if i in pt]
        if not kn or not an or (max(an) - hip_y) > 1.35 * torso:
            return "crouching: hips are not low"
    elif a == "running":
        if RANK in pt and LANK in pt:
            spread = math.dist(pt[RANK], pt[LANK])
            if spread < 0.9 * torso:
                return "running: no stride"
            bends = [angle(pt[h], pt[k], pt[an]) for h, k, an in ((RHIP, RKNE, RANK), (LHIP, LKNE, LANK)) if h in pt and k in pt and an in pt]
            if bends and min(bends) > 140:
                return "running: legs straight like a walk"
            if not any(i in pt and y(i) < y(NECK) + 0.6 * torso for i in wr) and len(wr) == 2 and abs(y(RWRI) - y(LWRI)) < 0.2 * torso:
                return "running: arms not pumping"
    elif a == "jumping":
        if not any(y(i) < y(NECK) for i in wr):
            return "jumping: arms not raised"
    elif a in ("standing", "walking", "punching"):
        if abs(x(NECK) - (pt[RHIP][0] + pt[LHIP][0]) / 2) > 0.5 * torso:
            return f"{a}: torso leaning too far"
        if a == "punching" and not any(sho in pt and wri in pt and abs(y(wri) - y(sho)) < 0.5 * torso
                                       and math.dist(pt[wri], pt[sho]) > 0.6 * torso
                                       for sho, wri in ((RSHO, RWRI), (LSHO, LWRI))):
            return "punching: no arm extended at shoulder height"
    return None
