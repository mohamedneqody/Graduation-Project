# -*- coding: utf-8 -*-
"""Protocol-identical reading-accuracy A/B: one checkpoint vs line crops GT."""
import os, sys, json, random, argparse
os.environ.setdefault("HF_HOME", r"D:\huggingface_cache")
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import difflib
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("--model-dir", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--n", type=int, default=120)
args = ap.parse_args()

GT = json.load(open("messy_rx_dataset_v8/line_ground_truth.json", encoding="utf-8"))
CROPS = "messy_rx_dataset_v8/line_crops"
rng = random.Random(7)
sample = rng.sample(GT, min(args.n, len(GT)))

from prescription_ocr_engine import PrescriptionOCREngine
engine = PrescriptionOCREngine(model_dir=args.model_dir)

images, texts = [], []
for entry in sample:
    img = Image.open(os.path.join(CROPS, entry["file"])).convert("RGB")
    images.append(img)
    texts.append(entry["text"])

results = engine.read_line_crops_batch(images)

def cer(a, b):
    if not a and not b: return 0.0
    return round(1 - difflib.SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio(), 4)

cers, details = [], []
for res, gt in zip(results, texts):
    c = cer(res.get("text", ""), gt)
    cers.append(c)
    details.append({"gt": gt, "read": res.get("text", ""), "cer": c, "conf": round(res.get("confidence", 0), 3)})

mean_cer = round(sum(cers) / len(cers), 4)
pass_015 = sum(1 for c in cers if c <= 0.15)
exact = sum(1 for c in cers if c == 0.0)
out = {"model_dir": args.model_dir, "n": len(cers), "mean_cer": mean_cer,
       "pass_cer_le_0.15": pass_015, "exact_matches": exact,
       "device": engine.trocr_device}
json.dump({"summary": out, "details": details}, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False))
