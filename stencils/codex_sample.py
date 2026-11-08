"""20-image GPT sample through Codex (ChatGPT plan), mirroring local tiles for comparison.

bodies: character 01, all 10 actions, figure told to fill the frame
faces : person 02, 6 emotions + 4 angles, with the local neutral photo as reference (-r)
usage: python3 stencils/codex_sample.py      (4 in parallel; skips images that exist)
"""
import os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from specs import ACTIONS, ANGLES, CHARACTERS, EMOTIONS, PEOPLE

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "work", "codex"); os.makedirs(OUT, exist_ok=True)
SCRIPT = os.path.expanduser("~/.claude/skills/codex-image/scripts/codex-image.sh")

char, cdesc = CHARACTERS[0]
person, pdesc = PEOPLE[1]
ref = os.path.join(HERE, "..", "work", "faces", person, "01_neutral_photo.png")

jobs = []
for act, phrase, orient in ACTIONS:
    fill = ("the figure fills the frame from left edge to right edge" if orient == "landscape"
            else "the figure fills the frame from top to bottom, head near the top edge, feet near the bottom edge")
    prompt = (f"full body photograph of {cdesc}, {phrase}, whole body visible from head to feet, {fill}, "
              f"plain light grey studio background, even soft lighting, realistic photo, correct human anatomy and "
              f"proportions, {orient} aspect, no text")
    jobs.append((f"body_{act}", "landscape" if orient == "landscape" else "portrait", prompt, None))

EMO = {k: v for k, v in EMOTIONS}
ANG = {k: v for k, v in ANGLES}
for key in ["04_sad", "05_crying", "06_angry", "08_afraid", "09_disgusted", "10_thinking"]:
    jobs.append((f"face_{key}", "square",
                 f"close-up head and shoulders portrait photograph of the same man as in the attached photo ({pdesc}), "
                 f"{EMO[key]}, a strong clear facial expression, looking at the camera, same framing as the attached "
                 f"photo, plain light grey studio background, soft even lighting, realistic photo, no text", ref))
for key in ["12_three_quarter_left", "15_profile_right", "16_looking_up", "17_looking_down"]:
    jobs.append((f"face_{key}", "square",
                 f"close-up head and shoulders portrait photograph of the same man as in the attached photo ({pdesc}), "
                 f"neutral expression, {ANG[key]}, head and shoulders fill the frame, plain light grey studio background, "
                 f"soft even lighting, realistic photo, no text", ref))


def run(job):
    name, shape, prompt, r = job
    out = os.path.join(OUT, name + ".png")
    if os.path.exists(out):
        return name, "skip"
    cmd = ["bash", SCRIPT, "-o", out, "-s", shape] + (["-r", r] if r else []) + [prompt]
    with open(os.path.join(OUT, name + ".log"), "w") as log:
        rc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log, timeout=420).returncode
    return name, "ok" if rc == 0 and os.path.exists(out) else f"failed rc={rc}"


if __name__ == "__main__":
    with ThreadPoolExecutor(4) as ex:
        for name, status in ex.map(run, jobs):
            print(name, status, flush=True)
