"""Small client and graph builders for Krita AI's ComfyUI on ArtPC.

Reach it with an ssh tunnel first (it listens on 127.0.0.1 only):
    ssh -f -N -L 18188:127.0.0.1:8188 you@your-gpu-pc
Krita must be open on ArtPC, since its ComfyUI only runs while Krita does.
"""
import json, os, time, uuid, urllib.parse, urllib.request

B = os.environ.get("COMFY_URL", "http://127.0.0.1:18188")
CKPT = "RealVisXL_V5.0_fp16.safetensors"
NEG = ("cropped, out of frame, cut off, extra limbs, extra arms, extra legs, extra fingers, fused fingers, "
       "missing limbs, deformed, bad anatomy, bad proportions, long neck, blurry, cartoon, painting, "
       "illustration, 3d render, text, watermark, nsfw")


# ---------- transport ----------
def upload(path):
    data = open(path, "rb").read()
    name = f"{uuid.uuid4().hex[:8]}_{os.path.basename(path)}"
    bound = uuid.uuid4().hex
    body = (f"--{bound}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + data + \
           f"\r\n--{bound}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{bound}--\r\n".encode()
    r = urllib.request.Request(B + "/upload/image", data=body,
                               headers={"Content-Type": f"multipart/form-data; boundary={bound}"})
    return json.load(urllib.request.urlopen(r))["name"]


def run(graph, timeout=900):
    req = urllib.request.Request(B + "/prompt", data=json.dumps({"prompt": graph, "client_id": uuid.uuid4().hex}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        resp = json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        raise RuntimeError("ComfyUI rejected graph: " + e.read().decode()[:2000])
    pid, t0 = resp["prompt_id"], time.time()
    while time.time() - t0 < timeout:
        h = json.load(urllib.request.urlopen(B + f"/history/{pid}"))
        if pid in h:
            if h[pid]["status"].get("status_str") == "error":
                raise RuntimeError("ComfyUI error: " + json.dumps(h[pid]["status"])[:2000])
            return h[pid]["outputs"]
        time.sleep(1.5)
    raise TimeoutError(pid)


def _get(item):
    q = urllib.parse.urlencode({"filename": item["filename"], "subfolder": item.get("subfolder", ""), "type": item["type"]})
    return urllib.request.urlopen(B + "/view?" + q).read()


def save_outputs(outputs, mapping):
    """mapping: {node_id: local_path}. Images by SaveImage, json by SavePoseKpsAsJsonFile (read from output dir)."""
    for node, path in mapping.items():
        o = outputs.get(node, {})
        imgs = o.get("images") or []
        if imgs:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "wb").write(_get(imgs[0]))


def fetch_json(subfolder, prefix):
    """SavePoseKpsAsJsonFile writes <prefix>_00001.json etc. Return the newest one."""
    last = None
    for n in range(1, 500):
        try:
            last = json.loads(_get({"filename": f"{prefix}_{n:05d}.json", "subfolder": subfolder, "type": "output"}))
        except Exception:
            break
    return last


# ---------- graph pieces ----------
class G:
    def __init__(self):
        self.g, self.n = {}, 0

    def add(self, cls, **inputs):
        self.n += 1
        k = str(self.n)
        self.g[k] = {"class_type": cls, "inputs": inputs}
        return k


def build(prompt, *, w, h, seed, steps=30, cfg=5.0, init_image=None, denoise=1.0,
          ipadapter_image=None, ipadapter_weight=0.6, pose_image=None, pose_strength=0.8,
          line_res=None, coarse=False, line_method="lineart", kps=False, tag="x", neg_extra=""):
    """One graph: generate photo -> 2x upscale -> line art (+ optional pose keypoints).

    Returns (graph_dict, {"photo": node, "line": node, "kps_prefix": str|None}).
    """
    x = G()
    ck = x.add("CheckpointLoaderSimple", ckpt_name=CKPT)
    model = [ck, 0]
    if ipadapter_image:
        ipa = x.add("IPAdapterModelLoader", ipadapter_file="ip-adapter_sdxl_vit-h.safetensors")
        cv = x.add("CLIPVisionLoader", clip_name="clip-vision_vit-h.safetensors")
        ref = x.add("LoadImage", image=ipadapter_image)
        m = x.add("IPAdapterAdvanced", model=model, ipadapter=[ipa, 0], image=[ref, 0], weight=ipadapter_weight,
                  weight_type="linear", combine_embeds="concat", start_at=0.0, end_at=1.0,
                  embeds_scaling="V only", clip_vision=[cv, 0])
        model = [m, 0]
    pos = x.add("CLIPTextEncode", clip=[ck, 1], text=prompt)
    neg = x.add("CLIPTextEncode", clip=[ck, 1], text=(neg_extra + ", " + NEG) if neg_extra else NEG)
    pos_c, neg_c = [pos, 0], [neg, 0]
    if pose_image:
        cn = x.add("ControlNetLoader", control_net_name="xinsir-controlnet-union-sdxl-1.0-promax.safetensors")
        cnt = x.add("SetUnionControlNetType", control_net=[cn, 0], type="openpose")
        pim = x.add("LoadImage", image=pose_image)
        ap = x.add("ControlNetApplyAdvanced", positive=pos_c, negative=neg_c, control_net=[cnt, 0], image=[pim, 0],
                   strength=pose_strength, start_percent=0.0, end_percent=0.8, vae=[ck, 2])
        pos_c, neg_c = [ap, 0], [ap, 1]
    if init_image:
        li = x.add("LoadImage", image=init_image)
        lat = x.add("VAEEncode", pixels=[li, 0], vae=[ck, 2])
    else:
        lat = x.add("EmptyLatentImage", width=w, height=h, batch_size=1)
    ks = x.add("KSampler", model=model, seed=seed, steps=steps, cfg=cfg, sampler_name="dpmpp_2m", scheduler="karras",
               positive=pos_c, negative=neg_c, latent_image=[lat, 0], denoise=denoise)
    dec = x.add("VAEDecode", samples=[ks, 0], vae=[ck, 2])
    photo = x.add("SaveImage", images=[dec, 0], filename_prefix=f"stencil2/{tag}_photo")
    out = {"photo": photo, "line": None, "kps_prefix": None}
    if line_res:
        big = x.add("ImageScaleBy", image=[dec, 0], upscale_method="lanczos", scale_by=2.0)
        if line_method == "pidinet":
            la = x.add("PiDiNetPreprocessor", image=[big, 0], safe="enable", resolution=line_res)
        elif line_method == "teed":
            la = x.add("TEEDPreprocessor", image=[big, 0], safe_steps=2, resolution=line_res)
        else:
            la = x.add("LineArtPreprocessor", image=[big, 0], coarse="enable" if coarse else "disable", resolution=line_res)
        out["line"] = x.add("SaveImage", images=[la, 0], filename_prefix=f"stencil2/{tag}_line")
    if kps:
        op = x.add("OpenposePreprocessor", image=[dec, 0], detect_hand="enable", detect_body="enable",
                   detect_face="disable", resolution=1024)
        out["kps_prefix"] = f"{tag}_kps"
        out["pose"] = x.add("SaveImage", images=[op, 0], filename_prefix=f"stencil2/{tag}_pose")
        x.add("SavePoseKpsAsJsonFile", pose_kps=[op, 1], filename_prefix=f"stencil2/{tag}_kps")
    return x.g, out


def generate(prompt, photo_path, line_path=None, kps_path=None, **kw):
    graph, out = build(prompt, kps=bool(kps_path), **kw)
    outputs = run(graph)
    m = {out["photo"]: photo_path}
    if out["line"] and line_path:
        m[out["line"]] = line_path
    if kps_path:
        m[out["pose"]] = kps_path.replace("_kps.json", "_pose.png")
    save_outputs(outputs, m)
    if kps_path:
        k = fetch_json("stencil2", out["kps_prefix"])
        os.makedirs(os.path.dirname(kps_path), exist_ok=True)
        json.dump(k, open(kps_path, "w"))
    return outputs
