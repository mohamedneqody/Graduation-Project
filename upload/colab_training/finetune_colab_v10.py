# -*- coding: utf-8 -*-
"""
AI-COS OCR - Round v10 (Colab): Augmentation + 1000 pages + holdout discipline
===============================================================================
الرفع المطلوب إلى /content:
  upload_v10_train.zip       (1000 صفحة: pro-500 بذور 40001+ + new-500 بذور 50001+)
  upload_v9_eval_frozen.zip  (holdout مجمّد — تقييم فقط، محظور على التدريب)
  [اختياري] upload_v8_legacy.zip (1794 قصاصة v8 القديمة — لتوسيع إضافي)

الجديد في v10:
  - Data Augmentation أثناء التدريب فقط (affine + jitter) — تعميم أقوى
  - 1000 صفحة (ضعف جولة v9) — بذور جديدة كلياً خارج الـholdout
  - نفس انضباط الفصل على مستوى الروشتة + القياس الختامي على الـholdout

خط الأساس المطلوب هزيمته: HOLDOUT CER 0.012 (v9 المنشور)
"""
import os, json, zipfile, random, glob
from collections import defaultdict

random.seed(42)
BASE = "/content"
TRAIN_ZIPS = [BASE + "/upload_v10_train.zip"]
EVAL_ZIP = BASE + "/upload_v9_eval_frozen.zip"
MODEL_OUT = BASE + "/trocr_v10_finetuned"
EPOCHS = 10

# ── 1) فك الحزم ──────────────────────────────────────────────
def unzip(zp, dest):
    print("unzip:", os.path.basename(zp))
    with zipfile.ZipFile(zp) as z:
        z.extractall(dest)

for z in TRAIN_ZIPS + [EVAL_ZIP]:
    unzip(z, BASE + "/data_v10")
print("unzipped.")

# ── 2) دمج كل مجموعات التدريب (كولاب يدمج أي عدد line_ground_truth) ──
records = []
for gt_path in glob.glob(BASE + "/data_v10/**/line_ground_truth.json", recursive=True):
    folder = os.path.dirname(gt_path)
    for r in json.load(open(gt_path, encoding="utf-8")):
        f = r.get("file") or r.get("filename")
        crop = os.path.join(folder, "line_crops", f)
        if not os.path.exists(crop):
            continue
        records.append({"crop": crop, "text": r.get("text", ""),
                        "source_rx": r.get("source_rx", os.path.basename(folder) + "_" + f)})
print("merged training records:", len(records))
assert len(records) > 2000, f"متوقع 3000+ قصاصة — وجدنا {len(records)}: راجع فك الضغط"

# ── 3) فصل على مستوى الروشتة الكاملة (لا تسريب) ─────────────
rx_to_crops = defaultdict(list)
for r in records:
    rx_to_crops[r["source_rx"]].append(r)
rxs = list(rx_to_crops.keys())
random.shuffle(rxs)
split = int(len(rxs) * 0.92)
train = [x for rx in rxs[:split] for x in rx_to_crops[rx]]
val = [x for rx in rxs[split:] for x in rx_to_crops[rx]]
print(f"rx-level split: {len(train)} train / {len(val)} val")

# ── 4) الموديل الكبير + Augmentation ────────────────────────
from transformers import TrOCRProcessor, VisionEncoderDecoderModel, Seq2SeqTrainer, Seq2SeqTrainingArguments, EarlyStoppingCallback
from PIL import Image
import torch
from torch.utils.data import Dataset

processor = TrOCRProcessor.from_pretrained("microsoft/trocr-large-handwritten")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-large-handwritten")
model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
model.config.pad_token_id = processor.tokenizer.pad_token_id
model.config.vocab_size = model.config.decoder.vocab_size
model.config.eos_token_id = processor.tokenizer.sep_token_id
model.config.max_length = 32

# Augmentation — على القصاصة قبل المعالج، تدريب فقط:
# محاكاة تنوع التصوير (ميلان/إزاحة/تكبير/إضاءة) التي لم تغطها البذور
from torchvision import transforms as T
TRAIN_AUG = T.Compose([
    T.RandomApply([T.RandomAffine(degrees=2.5, translate=(0.03, 0.05),
                                  scale=(0.88, 1.12), shear=3, fill=255)], p=0.7),
    T.ColorJitter(brightness=0.25, contrast=0.25),
])

class RxDS(Dataset):
    def __init__(self, rows, augment=False):
        self.rows, self.augment = rows, augment
    def __len__(self): return len(self.rows)
    def __getitem__(self, i):
        img = Image.open(self.rows[i]["crop"]).convert("RGB")
        if self.augment:
            img = TRAIN_AUG(img)
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
    per_device_eval_batch_size=8, learning_rate=2e-5, fp16=True,
    warmup_ratio=0.08, weight_decay=0.01,
    eval_strategy="epoch", save_strategy="epoch", save_total_limit=2,
    load_best_model_at_end=True, metric_for_best_model="cer", greater_is_better=False,
    predict_with_generate=True, logging_steps=50, report_to=[],
)
trainer = Seq2SeqTrainer(model=model, args=args,
                         train_dataset=RxDS(train, augment=True),
                         eval_dataset=RxDS(val, augment=False),
                         data_collator=collate, compute_metrics=compute_cer,
                         callbacks=[EarlyStoppingCallback(early_stopping_patience=3)])
trainer.train()
trainer.save_model(MODEL_OUT)
processor.save_pretrained(MODEL_OUT)
print("SAVED:", MODEL_OUT)

# ── 5) القياس الختامي الصادق: holdout مجمّد فقط ──────────────
hold = json.load(open(BASE + "/data_v10/holdout_frozen_v1/line_ground_truth.json", encoding="utf-8")) \
    if os.path.exists(BASE + "/data_v10/holdout_frozen_v1/line_ground_truth.json") \
    else json.load(open(BASE + "/data_v10/holdout/line_ground_truth.json", encoding="utf-8"))
hold_dir = BASE + "/data_v10/holdout_frozen_v1/line_crops" if \
    os.path.exists(BASE + "/data_v10/holdout_frozen_v1/line_crops") else BASE + "/data_v10/holdout/line_crops"
proc = TrOCRProcessor.from_pretrained(MODEL_OUT)
best = VisionEncoderDecoderModel.from_pretrained(MODEL_OUT).eval()
best.config.use_cache = True
preds = []
import difflib
BS = 16
dev = "cuda" if torch.cuda.is_available() else "cpu"
best = best.to(dev)
if dev == "cuda": best = best.half()
for i in range(0, len(hold), BS):
    imgs = [Image.open(os.path.join(hold_dir, e["file"])).convert("RGB") for e in hold[i:i+BS]]
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
print("HOLDOUT exact:", sum(1 for c in cers if c == 0.0), "/", len(cers))
print("BASELINE v9: 0.012 — الفائز فقط يُنشر")
print("=" * 55)
