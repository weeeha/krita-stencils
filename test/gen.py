"""Spike client for Krita AI's ComfyUI on ArtPC (through ssh tunnel on :18188).

bodies: pose skeleton -> xinsir union ControlNet (openpose) -> RealVisXL V5 -> photo
faces : text only, same seed per person, five emotions
every image also goes through LineArtPreprocessor (sketch) and OpenposePreprocessor (keypoints json for the check)
"""
import json, sys, time, uuid, urllib.request, os, io
B = "http://127.0.0.1:18188"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)
CKPT = "RealVisXL_V5.0_fp16.safetensors"
NEG = "cropped, out of frame, extra limbs, extra fingers, missing limbs, deformed, bad anatomy, blurry, cartoon, painting, illustration, text, watermark, nsfw"

def upload(path):
    data = open(path, "rb").read(); name = os.path.basename(path); bound = uuid.uuid4().hex
    body = (f"--{bound}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\nContent-Type: image/png\r\n\r\n").encode() + data + f"\r\n--{bound}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{bound}--\r\n".encode()
    r = urllib.request.Request(B + "/upload/image", data=body, headers={"Content-Type": f"multipart/form-data; boundary={bound}"})
    return json.load(urllib.request.urlopen(r))["name"]

def base_graph(pos, w, h, seed, steps=30, cfg=5.0):
    g = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": pos}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": NEG}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "dpmpp_2m", "scheduler": "karras", "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0], "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
    }
    return g

def add_outputs(g, prefix, pose_check=True):
    g["10"] = {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": f"stencil/{prefix}_photo"}}
    g["11"] = {"class_type": "LineArtPreprocessor", "inputs": {"image": ["6", 0], "coarse": "disable", "resolution": 1024}}
    g["12"] = {"class_type": "SaveImage", "inputs": {"images": ["11", 0], "filename_prefix": f"stencil/{prefix}_line"}}
    if pose_check:
        g["13"] = {"class_type": "OpenposePreprocessor", "inputs": {"image": ["6", 0], "detect_hand": "enable", "detect_body": "enable", "detect_face": "disable", "resolution": 1024}}
        g["14"] = {"class_type": "SavePoseKpsAsJsonFile", "inputs": {"pose_kps": ["13", 1], "filename_prefix": f"stencil/{prefix}_kps"}}

def body_graph(prompt, skeleton_name, seed, strength=0.85):
    g = base_graph(prompt, 832, 1216, seed)
    g["20"] = {"class_type": "ControlNetLoader", "inputs": {"control_net_name": "xinsir-controlnet-union-sdxl-1.0-promax.safetensors"}}
    g["21"] = {"class_type": "SetUnionControlNetType", "inputs": {"control_net": ["20", 0], "type": "openpose"}}
    g["22"] = {"class_type": "LoadImage", "inputs": {"image": skeleton_name}}
    g["23"] = {"class_type": "ControlNetApplyAdvanced", "inputs": {"positive": ["2", 0], "negative": ["3", 0], "control_net": ["21", 0], "image": ["22", 0], "strength": strength, "start_percent": 0.0, "end_percent": 0.85, "vae": ["1", 2]}}
    g["5"]["inputs"]["positive"] = ["23", 0]; g["5"]["inputs"]["negative"] = ["23", 1]
    return g

def run(g, timeout=600):
    cid = uuid.uuid4().hex
    r = urllib.request.Request(B + "/prompt", data=json.dumps({"prompt": g, "client_id": cid}).encode(), headers={"Content-Type": "application/json"})
    resp = json.load(urllib.request.urlopen(r))
    if "error" in resp or resp.get("node_errors"):
        raise SystemExit("ComfyUI rejected graph: " + json.dumps(resp)[:2000])
    pid = resp["prompt_id"]; t0 = time.time()
    while time.time() - t0 < timeout:
        h = json.load(urllib.request.urlopen(B + f"/history/{pid}"))
        if pid in h:
            st = h[pid]["status"]
            if st.get("status_str") == "error":
                raise SystemExit("ComfyUI error: " + json.dumps(st)[:2000])
            return h[pid]["outputs"]
        time.sleep(2)
    raise SystemExit("timeout")

def fetch(outputs, prefix):
    saved = []
    for node, o in outputs.items():
        for im in o.get("images", []):
            url = B + "/view?" + urllib.parse.urlencode({"filename": im["filename"], "subfolder": im.get("subfolder", ""), "type": im["type"]})
            data = urllib.request.urlopen(url).read()
            kind = "photo" if node == "10" else "line"
            p = os.path.join(OUT, f"{prefix}_{kind}.png"); open(p, "wb").write(data); saved.append(p)
    return saved

import urllib.parse
BODIES = [  # (pose, subject, action phrase)
    ("standing", "a 30 year old man, short hair, fitted grey t-shirt and dark jeans", "standing relaxed, arms at his sides, facing the camera"),
    ("walking", "a 25 year old woman, ponytail, fitted long-sleeve top and leggings", "walking towards the camera, mid stride"),
    ("running", "a 35 year old man, athletic build, running shorts and t-shirt", "running, side view, mid stride, leaning forward"),
    ("sitting", "a 60 year old man, grey beard, shirt and trousers", "sitting on a wooden stool, hands resting on his knees"),
    ("reaching", "a 40 year old woman, short hair, plain t-shirt and jeans", "reaching straight up with her right arm, left arm at her side"),
]
EMOTIONS = ["neutral expression", "big happy smile", "sad, on the verge of tears", "angry, furrowed brow, shouting", "surprised, eyes wide, mouth open"]

if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("bodies", "all"):
        for pose, subj, act in BODIES:
            sk = upload(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"pose_{pose}.png"))
            pos = f"full body photograph of {subj}, {act}, whole body visible from head to feet, feet on the floor, plain light grey studio background, even soft lighting, 50mm lens, sharp focus, realistic, high detail"
            t0 = time.time(); g = body_graph(pos, sk, seed=1001); add_outputs(g, f"body_{pose}")
            print(pose, fetch(run(g), f"body_{pose}"), f"{time.time()-t0:.0f}s", flush=True)
    if what in ("faces", "all"):
        for i, emo in enumerate(EMOTIONS):
            pos = f"close-up portrait photograph of a 45 year old woman, shoulder-length dark hair, light freckles, {emo}, facing the camera, plain light grey studio background, soft even lighting, 85mm lens, sharp focus, realistic, high detail"
            t0 = time.time(); g = base_graph(pos, 1024, 1024, seed=2024); add_outputs(g, f"face_{i}", pose_check=False)
            print("face", i, fetch(run(g), f"face_{i}"), f"{time.time()-t0:.0f}s", flush=True)
