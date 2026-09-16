# -*- coding: utf-8 -*-
"""
AI-COS OCR - PRO Round (Colab اشتراك مدفوع)
============================================
الرفع المطلوب إلى /content:
  upload_pro_train.zip        (500 صفحة جديدة - داتا Pro)
  upload_v9_eval_frozen.zip   (holdout مجمّد - تقييم فقط)
  trocr-large-handwritten/    (فولدر الموديل الكبير - نقطة البداية)

المميزات على النسخة المجانية: TrOCR-Large + 12 epoch + دفعات أكبر
الخرج: /content/trocr_pro_finetuned + قياس HOLDOUT الصادق
"""
import os, json, zipfile, random, glob
from collections import defaultdict

random.seed(42)
BASE = "/content"
TRAIN_ZIPS = [BASE + "/upload_pro_train.zip"]
EVAL_ZIP = BASE + "/upload_v9_eval_frozen.zip"
LOCAL_BASE = BASE + "/trocr-large-handwritten"   # الموديل الكبير المرفوع
MODEL_OUT = BASE + "/trocr_pro_finetuned"
EPOCHS = 12

def unzip(zp, dest):
    with zipfile.ZipFile(zp) as z:
        z.extractall(dest)

for z in TRAIN_ZIPS + [EVAL_ZIP]:
    print("unzip:", os.path.basename(z))
    unzip(z, BASE + "/data")
print("unzipped.")

records = []
for gt_path in glob.glob(BASE + "/data/*/line_ground_truth.json"):
    folder = os.path.dirname(gt_path)
    for r in json.load(open(gt_path, encoding="utf-8")):
        f = r.get("file") or r.get("filename")
        crop = os.path.join(folder, "line_crops", f)
        if not os.path.exists(crop):
            continue
        records.append({"crop": crop, "text": r.get("text", ""),
                        "source_rx": r.get("source_rx", os.path.dirname(crop))})
print("training records:", len(records))

rx_to_crops = defaultdict(list)
for r in records:
    rx_to_crops[r["source_rx"]].append(r)
rxs = list(rx_to_crops.keys())
random.shuffle(rxs)
split = int(len(rxs) * 0.92)   # الاشتراك يسمح بمجموعة تدريب أكبر
train = [x for rx in rxs[:split] for x in rx_to_crops[rx]]
val = [x for rx in rxs[split:] for x in rx_to_crops[rx]]
print("rx-level split:", len(train), "train /", len(val), "val")

from transformers import TrOCRProcessor, VisionEncoderDecoderModel, Seq2SeqTrainer, Seq2SeqTrainingArguments, EarlyStoppingCallback
from PIL import Image
import torch
from torch.utils.data import Dataset

# نقطة البداية: الموديل الكبير من الملفات المرفوعة (لا اعتماد على الشبكة)
processor = TrOCRProcessor.from_pretrained(LOCAL_BASE)
model = VisionEncoderDecoderModel.from_pretrained(LOCAL_BASE)
model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
model.config.pad_token_id = processor.tokenizer.pad_token_id
model.config.vocab_size = model.config.decoder.vocab_size
model.config.eos_token_id = processor.tokenizer.sep_token_id
model.config.max_length = 32

class RxDS(Dataset):
    def __init__(self, rows): self.rows = rows
    def __len__(self): return len(self.rows)
    def __getitem__(self, i):
        pv = processor(images=[Image.open(self.rows[i]["crop"]).convert("RGB")], return_tensors="pt").pixel_values[0]
        labels = processor.tokenizer(text=[self.rows[i]["text"]], padding="max_length", max_length=32, return_tensors="pt").input_ids[0]
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
    output_dir=MODEL_OUT, num_train_epochs=EPOCHS, per_device_train_batch_size=16,
    per_device_eval_batch_size=16, learning_rate=2e-5, fp16=True,
    warmup_ratio=0.1, weight_decay=0.01,
    eval_strategy="epoch", save_strategy="epoch", save_total_limit=2,
    load_best_model_at_end=True, metric_for_best_model="cer", greater_is_better=False,
    predict_with_generate=True, logging_steps=25, report_to=[],
)
trainer = Seq2SeqTrainer(model=model, args=args, train_dataset=RxDS(train),
                         eval_dataset=RxDS(val), data_collator=collate,
                         compute_metrics=compute_cer,
                         callbacks=[EarlyStoppingCallback(early_stopping_patience=3)])
trainer.train()
trainer.save_model(MODEL_OUT)
processor.save_pretrained(MODEL_OUT)
print("SAVED:", MODEL_OUT)

# ── القياس الختامي الصادق: holdout مجمّد فقط ──
unzip(EVAL_ZIP, BASE + "/holdout")
hold = json.load(open(BASE + "/holdout/line_ground_truth.json", encoding="utf-8"))
proc = TrOCRProcessor.from_pretrained(MODEL_OUT)
best = VisionEncoderDecoderModel.from_pretrained(MODEL_OUT).eval()
preds = []
import difflib
BS = 16
for i in range(0, len(hold), BS):
    imgs = [Image.open(BASE + "/holdout/line_crops/" + e["file"]).convert("RGB") for e in hold[i:i+BS]]
    pv = proc(images=imgs, return_tensors="pt").pixel_values
    preds += proc.batch_decode(best.generate(pv, max_length=32, num_beams=2), skip_special_tokens=True)
def cer(a, b):
    if not a and not b: return 0.0
    return round(1 - difflib.SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio(), 4)
cers = [cer(p, e["text"]) for p, e in zip(preds, hold)]
print("=" * 55)
print("HOLDOUT (unseen) MEAN CER:", round(sum(cers) / len(cers), 4))
print("HOLDOUT pass <=0.15:", sum(1 for c in cers if c <= 0.15), "/", len(cers))
print("HOLDOUT exact:", sum(1 for c in cers if c == 0.0), "/", len(cers))
print("خط الأساس المطلوب هزيمته: 0.2827 (النموذج الحالي على نفس الـholdout)")
print("=" * 55)
