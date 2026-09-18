# -*- coding: utf-8 -*-
"""
AI-COS OCR — ZERO-UPLOAD Grand Round (Colab)
=============================================
بدل رفع 9.63GB صور — نرفع ~5MB (مولّد + خطوط + كتالوجات)
وكولاب يولّد الداتا عنده ثم يدرب ثم يقيس. رفعك الكلي: ملف واحد صغير.

المطلوب قبل التشغيل:
  1. ارفع zero_upload_package.zip إلى /content (من المتصفح — 5MB)
  2. ارفع upload_v9_eval_frozen.zip إلى Drive (موجود عندك من قبل)
  3. Runtime → A100 GPU

التسلسل: توليد 2000 صفحة (بذور 60001+, mp×2) → دمج → تدريب TrOCR-Large
مع Augmentation → قياس HOLDOUT → حفظ النشر على Drive.
"""
import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
import json, zipfile, random, glob, shutil
from collections import defaultdict

random.seed(42)
BASE = "/content"

# ── 0) فك الحزمة الصغيرة ─────────────────────────────────────
with zipfile.ZipFile(BASE + "/zero_upload_package.zip") as z:
    z.extractall(BASE + "/gen")
os.chdir(BASE + "/gen")           # المولّد يقرأ fonts/ والكتالوجات من هنا
print("package extracted:", os.listdir("."))

# ── 1) التوليد على كولاب (2000 صفحة، توازي ×2) ───────────────
import subprocess
r = subprocess.run(["python", "generate_messy_colab.py"],
                   env={**os.environ, "GEN_PAGES": "2000", "GEN_SEED": "60001",
                        "GEN_OUT": BASE + "/data_zero/messy_grand"},
                   capture_output=True, text=True)
print(r.stdout[-800:]); print(r.stderr[-500:] if r.returncode else "")
assert r.returncode == 0, "generation failed"

# ── 2) الـholdout من Drive ───────────────────────────────────
from google.colab import drive
drive.mount('/content/drive')
unzip_hold = BASE + "/data_zero/holdout"
with zipfile.ZipFile(BASE + "/drive/MyDrive/upload_v9_eval_frozen.zip") as z:
    z.extractall(unzip_hold)

# ── 3) فصل على مستوى الروشتة ─────────────────────────────────
gt = json.load(open(BASE + "/data_zero/messy_grand/line_ground_truth.json", encoding="utf-8"))
from collections import defaultdict
rx_to_crops = defaultdict(list)
for e in gt:
    rx_to_crops[e.get("source_rx", e["file"])].append(e)
rxs = list(rx_to_crops.keys()); random.shuffle(rxs)
split = int(len(rxs) * 0.92)
train_rx, val_rx = set(rxs[:split]), set(rxs[split:])
print(f"pages: {len(rxs)} | train {len(train_rx)} / val {len(val_rx)}")

from transformers import TrOCRProcessor, VisionEncoderDecoderModel, Seq2SeqTrainer, Seq2SeqTrainingArguments, EarlyStoppingCallback
from PIL import Image
import torch
from torch.utils.data import Dataset
from torchvision import transforms as T

processor = TrOCRProcessor.from_pretrained("microsoft/trocr-large-handwritten")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-large-handwritten")
model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
model.config.pad_token_id = processor.tokenizer.pad_token_id
model.config.vocab_size = model.config.decoder.vocab_size
model.config.eos_token_id = processor.tokenizer.sep_token_id
model.config.max_length = 32

TRAIN_AUG = T.Compose([
    T.RandomApply([T.RandomAffine(degrees=2.5, translate=(0.03, 0.05),
                                  scale=(0.88, 1.12), shear=3, fill=255)], p=0.7),
    T.ColorJitter(brightness=0.25, contrast=0.25),
])
CROP_DIR = BASE + "/data_zero/messy_grand/line_crops"

class RxDS(Dataset):
    def __init__(self, entries, augment=False):
        self.entries, self.augment = entries, augment
    def __len__(self): return len(self.entries)
    def __getitem__(self, i):
        e = self.entries[i]
        img = Image.open(CROP_DIR + "/" + e["file"]).convert("RGB")
        if self.augment: img = TRAIN_AUG(img)
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
    cer = evaluate.load("cer")
    ids = pred.label_ids
    ids[ids == -100] = processor.tokenizer.pad_token_id
    return {"cer": cer.compute(predictions=processor.batch_decode(pred.predictions, skip_special_tokens=True),
                                references=processor.batch_decode(ids, skip_special_tokens=True))}

MODEL_OUT = BASE + "/trocr_zero_finetuned"
args = Seq2SeqTrainingArguments(
    output_dir=MODEL_OUT, num_train_epochs=10, per_device_train_batch_size=8,
    per_device_eval_batch_size=8, learning_rate=2e-5, fp16=True,
    warmup_ratio=0.08, weight_decay=0.01,
    eval_strategy="epoch", save_strategy="epoch", save_total_limit=2,
    load_best_model_at_end=True, metric_for_best_model="cer", greater_is_better=False,
    predict_with_generate=True, logging_steps=50, report_to=[],
)
trainer = Seq2SeqTrainer(model=model, args=args,
                         train_dataset=RxDS([e for rx in train_rx for e in rx_to_crops[rx]], augment=True),
                         eval_dataset=RxDS([e for rx in val_rx for e in rx_to_crops[rx]]),
                         data_collator=collate, compute_metrics=compute_cer,
                         callbacks=[EarlyStoppingCallback(early_stopping_patience=3)])
trainer.train()
trainer.save_model(MODEL_OUT)
processor.save_pretrained(MODEL_OUT)
print("SAVED:", MODEL_OUT)

# ── 4) القياس الختامي: holdout مجمّد (Windows-font domain) ────
hold = json.load(open(glob.glob(unzip_hold + "/**/line_ground_truth.json", recursive=True)[0], encoding="utf-8"))
hold_dir = glob.glob(unzip_hold + "/**/line_crops", recursive=True)[0]
proc = TrOCRProcessor.from_pretrained(MODEL_OUT)
best = VisionEncoderDecoderModel.from_pretrained(MODEL_OUT).eval()
best.config.use_cache = True
best = best.half().cuda()
preds = []
import difflib
for i in range(0, len(hold), 16):
    imgs = [Image.open(os.path.join(hold_dir, e["file"])).convert("RGB") for e in hold[i:i+16]]
    pv = proc(images=imgs, return_tensors="pt").pixel_values.half().cuda()
    preds += proc.batch_decode(best.generate(pv, max_length=32, num_beams=2), skip_special_tokens=True)
def cer(a, b):
    if not a and not b: return 0.0
    return round(1 - difflib.SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio(), 4)
cers = [cer(p, e["text"]) for p, e in zip(preds, hold)]
print("=" * 55)
print("HOLDOUT (unseen) MEAN CER:", round(sum(cers) / len(cers), 4))
print("HOLDOUT pass <=0.15:", sum(1 for c in cers if c <= 0.15), "/", len(cers))
print("BASELINE v9: 0.012 — انشر فقط إذا كان أقل أو مساوياً")
print("=" * 55)

# ── 5) حفظ نشر النموذج الفائز على Drive ──────────────────────
KEEP = {"model.safetensors", "config.json", "generation_config.json",
        "tokenizer.json", "tokenizer_config.json", "vocab.json",
        "merges.txt", "special_tokens_map.json", "preprocessor_config.json"}
OUT_ZIP = BASE + "/v10_deploy.zip"
with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_STORED) as z:
    for f in sorted(os.listdir(MODEL_OUT)):
        if f in KEEP:
            z.write(os.path.join(MODEL_OUT, f), f)
shutil.copy(OUT_ZIP, BASE + "/drive/MyDrive/v10_deploy.zip")
print("✅ MyDrive/v10_deploy.zip —", round(os.path.getsize(BASE + "/drive/MyDrive/v10_deploy.zip")/1e9, 2), "GB")
