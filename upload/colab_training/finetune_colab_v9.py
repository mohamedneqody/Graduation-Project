# -*- coding: utf-8 -*-
"""
AI-COS OCR - Colab Training Round v9 (holdout-disciplined)
الرفع المطلوب: upload_v9_train.zip + upload_v9_eval_frozen.zip
التدريب: دمج المجموعات -> فصل validation على مستوى الروشتة الكاملة
التقييم الختامي: holdout_frozen_v1 فقط - الرقم الصادق (قارن مع 0.2827)
"""
import os, json, zipfile, random, glob
from collections import defaultdict

random.seed(42)
BASE = "/content"
TRAIN_ZIPS = [BASE + "/upload_v9_train.zip"]
EVAL_ZIP = BASE + "/upload_v9_eval_frozen.zip"
MODEL_OUT = BASE + "/trocr_v9_finetuned"

def unzip(zp, dest):
    with zipfile.ZipFile(zp) as z:
        z.extractall(dest)

for z in TRAIN_ZIPS + [EVAL_ZIP]:
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
print("merged training records:", len(records))

rx_to_crops = defaultdict(list)
for r in records:
    rx_to_crops[r["source_rx"]].append(r)
rxs = list(rx_to_crops.keys())
random.shuffle(rxs)
split = int(len(rxs) * 0.9)
train = [x for rx in rxs[:split] for x in rx_to_crops[rx]]
val = [x for rx in rxs[split:] for x in rx_to_crops[rx]]
print("rx-level split:", len(train), "train /", len(val), "val lines")

from transformers import TrOCRProcessor, VisionEncoderDecoderModel, Seq2SeqTrainer, Seq2SeqTrainingArguments, EarlyStoppingCallback
from PIL import Image
import torch
from torch.utils.data import Dataset

processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
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
    output_dir=MODEL_OUT, num_train_epochs=6, per_device_train_batch_size=8,
    per_device_eval_batch_size=8, learning_rate=3e-5, fp16=True,
    eval_strategy="epoch", save_strategy="epoch", load_best_model_at_end=True,
    metric_for_best_model="cer", greater_is_better=False,
    predict_with_generate=True, logging_steps=20, report_to=[],
)
trainer = Seq2SeqTrainer(model=model, args=args, train_dataset=RxDS(train),
                         eval_dataset=RxDS(val), data_collator=collate,
                         compute_metrics=compute_cer,
                         callbacks=[EarlyStoppingCallback(early_stopping_patience=2)])
trainer.train()
trainer.save_model(MODEL_OUT)
processor.save_pretrained(MODEL_OUT)
print("SAVED:", MODEL_OUT)

unzip(EVAL_ZIP, BASE + "/holdout")
hold = json.load(open(BASE + "/holdout/line_ground_truth.json", encoding="utf-8"))
proc = TrOCRProcessor.from_pretrained(MODEL_OUT)
best = VisionEncoderDecoderModel.from_pretrained(MODEL_OUT).eval()
preds = []
import difflib
for i in range(0, len(hold), 8):
    imgs = [Image.open(BASE + "/holdout/line_crops/" + e["file"]).convert("RGB") for e in hold[i:i+8]]
    pv = proc(images=imgs, return_tensors="pt").pixel_values
    preds += proc.batch_decode(best.generate(pv, max_length=32, num_beams=2), skip_special_tokens=True)
def cer(a, b):
    if not a and not b: return 0.0
    return round(1 - difflib.SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio(), 4)
cers = [cer(p, e["text"]) for p, e in zip(preds, hold)]
print("=" * 50)
print("HOLDOUT (unseen) MEAN CER:", round(sum(cers) / len(cers), 4))
print("HOLDOUT pass <=0.15:", sum(1 for c in cers if c <= 0.15), "/", len(cers))
print("قارن مع خط الأساس 0.2827")
print("=" * 50)
