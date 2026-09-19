# -*- coding: utf-8 -*-
"""Builder: assembles finetune_colab_v11.py (generator inline + training + eval)."""
import ast

gen_core = open("_gen_core.py", encoding="utf-8").read()

header = '''# -*- coding: utf-8 -*-
"""
AI-COS OCR - Round v11 FINAL (one file: generator + training + eval)
====================================================================
الرفع: هذا الملف فقط. كولاب يولد 2000 صفحة بنفسه (خطوط لينكس - تنوع
مجاني)، يدرب من أوزان v9 على Drive، ويقيس على holdout_frozen_v1.
خط الأساس: 0.0152 - الفائز فقط ينشر.
"""
import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
import io, json, math, random, glob, shutil, subprocess, zipfile
from collections import defaultdict

random.seed(42)
BASE = "/content"
MODEL_OUT = BASE + "/trocr_v11_finetuned"
EPOCHS = 6
GEN_SEED = 60001
GEN_PAGES = 2000

# ============== 1) المولد (inline) ==============
print("=== 1/5 توليد الداتا على كولاب ===")
from faker import Faker
fake = Faker("en_US")
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import numpy as np, cv2

with open("real_drugs.json", encoding="utf-8") as f:
    _REAL = json.load(f)
try:
    with open("generic_drugs.json", encoding="utf-8") as f:
        _GEN = json.load(f)
    REAL_DRUGS_DB = list(_REAL) + [{"drug_id": "gen" + str(i), "name": n.title()} for i, n in enumerate(_GEN)]
except FileNotFoundError:
    REAL_DRUGS_DB = list(_REAL)
print("catalog:", len(REAL_DRUGS_DB), "names")

W, H = 1000, 1300
GEN_OUT = BASE + "/data_v11/messy_grand"
IMG_DIR = os.path.join(GEN_OUT, "images")
CROP_DIR = os.path.join(GEN_OUT, "line_crops")
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(CROP_DIR, exist_ok=True)

def _find_fonts():
    import glob as _g
    cands = []
    for pat in ["/usr/share/fonts/**/*Italic*.ttf", "/usr/share/fonts/**/*italic*.ttf",
                "/usr/share/fonts/**/*Oblique*.ttf"]:
        cands += _g.glob(pat, recursive=True)
    if not cands:
        cands = _g.glob("/usr/share/fonts/**/*.ttf", recursive=True)
    printed = None
    for p in _g.glob("/usr/share/fonts/**/DejaVuSans.ttf", recursive=True):
        printed = p; break
    return cands, (printed or (cands[0] if cands else None))

FONT_CANDIDATES, PRINTED_FONT_PATH = _find_fonts()
print("fonts found:", len(FONT_CANDIDATES))
assert FONT_CANDIDATES, "no fonts on Colab!"

'''

footer = '''
# ============== تشغيل التوليد (متسلسل بدقة البذور) ==============
records, all_crops = [], []
DIFFS = ["easy", "medium", "hard"]
for i in range(1, GEN_PAGES + 1):
    random.seed(GEN_SEED + i)
    fake.seed_instance(GEN_SEED + i)
    rec = render_prescription(i, DIFFS[i % 3])
    records.append(rec)
    all_crops.extend(rec.get("cropped_data", []))
    if i % 250 == 0:
        print("  " + str(i) + "/" + str(GEN_PAGES))

json.dump(records, open(os.path.join(GEN_OUT, "ground_truth.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
json.dump(all_crops, open(os.path.join(GEN_OUT, "line_ground_truth.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("generated: " + str(len(records)) + " pages / " + str(len(all_crops)) + " crops")

# ============== 2) الـholdout المجمد من Drive ==============
print("=== 2/5 الـholdout من Drive ===")
from google.colab import drive
drive.mount("/content/drive")
MD = "/content/drive/MyDrive"
HOLD_ZIP = MD + "/upload_v9_eval_frozen.zip"
HOLD_DIR = BASE + "/holdout_frozen"
with zipfile.ZipFile(HOLD_ZIP) as z:
    z.extractall(HOLD_DIR)
hold_gt_path = glob.glob(HOLD_DIR + "/**/line_ground_truth.json", recursive=True)[0]
hold = json.load(open(hold_gt_path, encoding="utf-8"))
hold_crops_dir = os.path.dirname(hold_gt_path)
FORBIDDEN_TEXTS = set(e["text"].strip().lower() for e in hold)
print("holdout: " + str(len(hold)) + " crops - texts frozen out of training")

# ============== 3) دمج + فلترة التسريب + فصل ==============
print("=== 3/5 الدمج والفصل ===")
train, val = [], []
rx_to_crops = defaultdict(list)
leaked = 0
for e in all_crops:
    txt = (e.get("text") or "").strip().lower()
    if txt in FORBIDDEN_TEXTS:
        leaked += 1
        continue
    rx_to_crops[e.get("source_rx", e["file"])].append(e)
rxs = list(rx_to_crops.keys())
random.shuffle(rxs)
split = int(len(rxs) * 0.92)
for rx in rxs[:split]:
    train += rx_to_crops[rx]
for rx in rxs[split:]:
    val += rx_to_crops[rx]
print("train: " + str(len(train)) + " | val: " + str(len(val)) + " | leak-blocked: " + str(leaked))

# ============== 4) الأوزان: v9 من Drive + التدريب ==============
print("=== 4/5 التدريب من أوزان v9 ===")
from transformers import TrOCRProcessor, VisionEncoderDecoderModel, Seq2SeqTrainer, Seq2SeqTrainingArguments, EarlyStoppingCallback
import torch
from torch.utils.data import Dataset
from torchvision import transforms as T

with zipfile.ZipFile(MD + "/upload_v9_model.zip") as z:
    z.extractall(BASE + "/v9_base")
v9_base = BASE + "/v9_base"
for root, _, fs in os.walk(v9_base):
    if "model.safetensors" in fs:
        v9_base = root
        break
print("v9 weights:", v9_base)

processor = TrOCRProcessor.from_pretrained(v9_base)
model = VisionEncoderDecoderModel.from_pretrained(v9_base)
model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
model.config.pad_token_id = processor.tokenizer.pad_token_id
model.config.vocab_size = model.config.decoder.vocab_size
model.config.eos_token_id = processor.tokenizer.sep_token_id
model.config.max_length = 32

TRAIN_AUG = T.Compose([
    T.RandomApply([T.RandomAffine(degrees=1.5, translate=(0.02, 0.03),
                                  scale=(0.92, 1.08), fill=255)], p=0.5),
])

class RxDS(Dataset):
    def __init__(self, rows, augment=False):
        self.rows = rows
        self.augment = augment
    def __len__(self):
        return len(self.rows)
    def __getitem__(self, i):
        e = self.rows[i]
        img = Image.open(io.BytesIO(e["image"])) if isinstance(e.get("image"), bytes) else Image.open(e["crop"])
        img = img.convert("RGB")
        if self.augment:
            img = TRAIN_AUG(img)
        pv = processor(images=[img], return_tensors="pt").pixel_values[0]
        labels = processor.tokenizer(text=[e["text"]], padding="max_length",
                                     max_length=32, return_tensors="pt").input_ids[0]
        labels[labels == processor.tokenizer.pad_token_id] = -100
        return {"pixel_values": pv, "labels": labels}

def collate(features):
    pv = torch.stack([f["pixel_values"] for f in features])
    mx = max(f["labels"].shape[-1] for f in features)
    labels = torch.full((len(features), mx), -100, dtype=torch.long)
    for i, f in enumerate(features):
        labels[i, : f["labels"].shape[-1]] = f["labels"]
    return {"pixel_values": pv, "labels": labels}

def compute_cer(pred):
    import evaluate
    cer_m = evaluate.load("cer")
    ids = pred.label_ids
    ids[ids == -100] = processor.tokenizer.pad_token_id
    return {"cer": cer_m.compute(
        predictions=processor.batch_decode(pred.predictions, skip_special_tokens=True),
        references=processor.batch_decode(ids, skip_special_tokens=True))}

args = Seq2SeqTrainingArguments(
    output_dir=MODEL_OUT, num_train_epochs=EPOCHS, per_device_train_batch_size=8,
    per_device_eval_batch_size=8, learning_rate=1e-5, fp16=True,
    warmup_ratio=0.08, weight_decay=0.01,
    eval_strategy="epoch", save_strategy="epoch", save_total_limit=2,
    load_best_model_at_end=True, metric_for_best_model="cer", greater_is_better=False,
    predict_with_generate=True, logging_steps=50, report_to=[],
)
trainer = Seq2SeqTrainer(model=model, args=args,
                         train_dataset=RxDS(train, augment=True),
                         eval_dataset=RxDS(val),
                         data_collator=collate, compute_metrics=compute_cer,
                         callbacks=[EarlyStoppingCallback(early_stopping_patience=3)])
trainer.train()
trainer.save_model(MODEL_OUT)
processor.save_pretrained(MODEL_OUT)
print("SAVED: " + MODEL_OUT)

# ============== 5) القياس الختامي: holdout مجمد ==============
print("=== 5/5 القياس الختامي ===")
proc = TrOCRProcessor.from_pretrained(MODEL_OUT)
best = VisionEncoderDecoderModel.from_pretrained(MODEL_OUT).eval()
best.config.use_cache = True
dev = "cuda" if torch.cuda.is_available() else "cpu"
best = best.to(dev)
if dev == "cuda":
    best = best.half()
preds = []
import difflib
for i in range(0, len(hold), 16):
    imgs = [Image.open(os.path.join(hold_crops_dir, e["file"])).convert("RGB") for e in hold[i:i + 16]]
    pv = proc(images=imgs, return_tensors="pt").pixel_values.to(dev)
    if dev == "cuda":
        pv = pv.half()
    preds += proc.batch_decode(best.generate(pv, max_length=32, num_beams=2), skip_special_tokens=True)

def cer(a, b):
    if not a and not b:
        return 0.0
    return round(1 - difflib.SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio(), 4)

cers = [cer(p, e["text"]) for p, e in zip(preds, hold)]
print("=" * 55)
print("HOLDOUT (unseen) MEAN CER: " + str(round(sum(cers) / len(cers), 4)))
print("HOLDOUT pass <=0.15: " + str(sum(1 for c in cers if c <= 0.15)) + " / " + str(len(cers)))
print("HOLDOUT exact: " + str(sum(1 for c in cers if c == 0.0)) + " / " + str(len(cers)))
print("BASELINE v9: 0.0152 - deploy only if lower")
print("=" * 55)
'''

script = header + gen_core + footer
open("finetune_colab_v11.py", "w", encoding="utf-8").write(script)
ast.parse(script)
print("v11 FINAL assembled + syntax OK:", len(script), "chars")
