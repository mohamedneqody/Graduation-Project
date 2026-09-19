# -*- coding: utf-8 -*-
"""
AI-COS OCR — Round v11 (Colab): من أوزان v9 + توليد على كولاب (صفر رفع كبير)
=============================================================================
على Drive لازم يكون موجود (لا تمسحها):
  upload_v9_model.zip          (أوزان v9 — أنت رافعها ✓)
  upload_v9_eval_frozen.zip    (holdout — موجودة ✓)
  zero_upload/                 (فولدر الخطوط والكتالوجات — موجود ✓)
  upload_pro_train.zip         (داتا pro — موجودة ✓)

في كولاب: Runtime → A100 → شغّل الخليتين تحت.
الخلاصة: توليد 2000 صفحة على كولاب + داتا pro → ~7400 قصاصة
→ تدريب من أوزان v9 (LR 1e-5، بلا ColorJitter، 6 epochs)
→ قياس HOLDOUT — خط الأساس 0.0152 — الفائز فقط يُنشر.
"""
import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
import json, zipfile, random, glob, shutil, subprocess
from collections import defaultdict

random.seed(42)
BASE = "/content"
MODEL_OUT = BASE + "/trocr_v11_finetuned"
EPOCHS = 6

# ── 0) Drive + حصر المسارات ──────────────────────────────────
import os as _os
from google.colab import drive as _drive_mod
if not _os.path.exists("/content/drive/MyDrive"):
    _drive_mod.mount('/content/drive')
MD = BASE + "/drive/MyDrive"

# ── 1) تجهيز مجلد التوليد (من فولدر zero_upload الموجود في Drive) ──
GEN = BASE + "/gen"
shutil.rmtree(GEN, ignore_errors=True)
shutil.copytree(MD + "/zero_upload", GEN, ignore=shutil.ignore_patterns("_gen_smoke*", "images", "*.png"))
print("gen folder:", sorted(os.listdir(GEN)))

# ── 2) فك حزم Drive ─────────────────────────────────────────
for zp, dest in [("upload_pro_train.zip", BASE + "/data_v11/pro"),
                 ("upload_v9_eval_frozen.zip", BASE + "/data_v11/holdout"),
                 ("upload_v9_model.zip", BASE + "/data_v11/v9model")]:
    if not os.path.exists(MD + "/" + zp):
        print("⚠️ اختياري — تخطي:", zp)
        continue
    with zipfile.ZipFile(MD + "/" + zp) as z:
        z.extractall(dest)
    print("extracted:", zp)

v9_base = BASE + "/data_v11/v9model"
for root, _, fs in os.walk(v9_base):
    if "model.safetensors" in fs:
        v9_base = root; break
print("v9 weights at:", v9_base)

# ── 3) توليد 2000 صفحة جديدة على كولاب (بذور 60001+) ─────────
print("=== توليد الداتا (~40-50 دقيقة) ===")
os.chdir(GEN)
r = subprocess.run(["python", "generate_messy_colab.py"],
                   env={**os.environ, "GEN_PAGES": "2000", "GEN_SEED": "60001",
                        "GEN_OUT": BASE + "/data_v11/messy_grand"},
                   capture_output=True, text=True)
print(r.stdout[-500:])
assert r.returncode == 0, "generation failed: " + r.stderr[-400:]
os.chdir(BASE)

# ── 4) دمج المجموعتين (المولدة + pro) مع dedup ───────────────
records, seen = [], set()
dups = 0
for gt_path in glob.glob(BASE + "/data_v11/**/line_ground_truth.json", recursive=True):
    if "holdout" in gt_path.replace("\\\\", "/"):
        continue  # الـholdout محروم من التدريب
    folder = os.path.dirname(gt_path)
    for e in json.load(open(gt_path, encoding="utf-8")):
        f = e.get("file") or e.get("filename")
        crop = os.path.join(folder, "line_crops", f)
        if not os.path.exists(crop):
            continue
        key = ((e.get("source_rx") or "") + "|" + (e.get("text") or ""))
        if key in seen:
            dups += 1; continue
        seen.add(key)
        records.append({"crop": crop, "text": e.get("text", ""),
                        "source_rx": (e.get("source_rx") or f)})
print(f"merged: {len(records)} unique crops (dedup skipped {dups})")

# ── 5) فصل على مستوى الروشتة الكاملة 92/8 ────────────────────
rx_to_crops = defaultdict(list)
for r in records:
    rx_to_crops[r["source_rx"]].append(r)
rxs = list(rx_to_crops.keys()); random.shuffle(rxs)
split = int(len(rxs) * 0.92)
train = [x for rx in rxs[:split] for x in rx_to_crops[rx]]
val = [x for rx in rxs[split:] for x in rx_to_crops[rx]]
print(f"rx-level split: {len(train)} train / {len(val)} val")

# ── 6) الأوزان: v9 (نكمل منه — لا من الصفر) ─────────────────
from transformers import TrOCRProcessor, VisionEncoderDecoderModel, Seq2SeqTrainer, Seq2SeqTrainingArguments, EarlyStoppingCallback
from PIL import Image
import torch
from torch.utils.data import Dataset
from torchvision import transforms as T

processor = TrOCRProcessor.from_pretrained(v9_base)
model = VisionEncoderDecoderModel.from_pretrained(v9_base)
model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
model.config.pad_token_id = processor.tokenizer.pad_token_id
model.config.vocab_size = model.config.decoder.vocab_size
model.config.eos_token_id = processor.tokenizer.sep_token_id
model.config.max_length = 32

# v11 recipe: بلا ColorJitter (قاتل الثقة) — affine خفيف فقط
TRAIN_AUG = T.Compose([
    T.RandomApply([T.RandomAffine(degrees=1.5, translate=(0.02, 0.03),
                                  scale=(0.92, 1.08), fill=255)], p=0.5),
])

class RxDS(Dataset):
    def __init__(self, rows, augment=False):
        self.rows, self.augment = rows, augment
    def __len__(self): return len(self.rows)
    def __getitem__(self, i):
        img = Image.open(self.rows[i]["crop"]).convert("RGB")
        if self.augment: img = TRAIN_AUG(img)
        pv = processor(images=[img], return_tensors="pt").pixel_values[0]
        labels = processor.tokenizer(text=[self.rows[i]["text"]], padding="max_length",
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
    cer = evaluate.load("cer")
    ids = pred.label_ids
    ids[ids == -100] = processor.tokenizer.pad_token_id
    return {"cer": cer.compute(predictions=processor.batch_decode(pred.predictions, skip_special_tokens=True),
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
print("SAVED:", MODEL_OUT)

# ── 7) القياس الختامي: holdout مجمّد ─────────────────────────
hold_gt = glob.glob(BASE + "/data_v11/holdout/**/line_ground_truth.json", recursive=True)[0]
hold_dir = os.path.dirname(hold_gt)
hold = json.load(open(hold_gt, encoding="utf-8"))
proc = TrOCRProcessor.from_pretrained(MODEL_OUT)
best = VisionEncoderDecoderModel.from_pretrained(MODEL_OUT).eval()
best.config.use_cache = True
dev = "cuda" if torch.cuda.is_available() else "cpu"
best = best.to(dev)
if dev == "cuda": best = best.half()
preds = []
import difflib
for i in range(0, len(hold), 16):
    imgs = [Image.open(os.path.join(hold_dir, e["file"])).convert("RGB") for e in hold[i:i+16]]
    pv = processor(images=imgs, return_tensors="pt").pixel_values.to(dev)
    if dev == "cuda": pv = pv.half()
    preds += proc.batch_decode(best.generate(pv, max_length=32, num_beams=2), skip_special_tokens=True)
def cer(a, b):
    if not a and not b: return 0.0
    return round(1 - difflib.SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio(), 4)
cers = [cer(p, e["text"]) for p, e in zip(preds, hold)]
print("=" * 55)
print("HOLDOUT (unseen) MEAN CER:", round(sum(cers) / len(cers), 4))
print("HOLDOUT pass <=0.15:", sum(1 for c in cers if c <= 0.15), "/", len(cers))
print("BASELINE v9 (local holdout): 0.0152 — انشر فقط إذا كان أقل")
print("=" * 55)

# ── 8) حفظ النشر على Drive ───────────────────────────────────
KEEP = {"model.safetensors", "config.json", "generation_config.json",
        "tokenizer.json", "tokenizer_config.json", "vocab.json",
        "merges.txt", "special_tokens_map.json", "preprocessor_config.json"}
OUT_ZIP = BASE + "/v11_deploy.zip"
with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_STORED) as z:
    for f in sorted(os.listdir(MODEL_OUT)):
        if f in KEEP:
            z.write(os.path.join(MODEL_OUT, f), f)
shutil.copy(OUT_ZIP, MD + "/v11_deploy.zip")
print("✅ MyDrive/v11_deploy.zip —", round(os.path.getsize(MD + "/v11_deploy.zip")/1e9, 2), "GB")
