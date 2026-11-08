"""Re-run the body check on finished tiles. With --apply, failures lose _ok and become _flagged,
so the next `SEED_OFFSET=<n> python3 stencils/bodies.py` regenerates them."""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from check import body_check
from specs import ACTIONS
ORIENT = {a: o for a, _, o in ACTIONS}
apply = "--apply" in sys.argv
bad = []
for k in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "work", "bodies", "*", "*_kps.json"))):
    base = k[:-9]; act = os.path.basename(base)
    if "_try" in act or not (os.path.exists(base + "_ok") or os.path.exists(base + "_flagged")):
        continue
    land = ORIENT[act] == "landscape"; w, h = (1216, 832) if land else (832, 1216)
    ok, why, _ = body_check(json.load(open(k)), w, h, landscape=land, action=act)
    if not ok:
        bad.append((base.split("bodies/")[1], why))
        if apply and os.path.exists(base + "_ok"):
            os.remove(base + "_ok"); open(base + "_flagged", "w").write(json.dumps(why))
for b, why in bad:
    print(b, "; ".join(why))
print(len(bad), "failing")
