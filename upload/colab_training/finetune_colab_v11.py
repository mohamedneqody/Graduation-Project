# -*- coding: utf-8 -*-
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

# رفع الكتالوجات الصغيرة من جهازك (تلقائي عند التشغيل)
from google.colab import files as _fup
print("ارفع: real_drugs.json ثم generic_drugs.json (من مجلد colab_training)")
_up = _fup.upload()
for _n, _d in _up.items():
    open(_n, "wb").write(_d)

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

# ----------------------------------------------------------------------
# DIFFICULTY TIERS
# ----------------------------------------------------------------------
DIFFICULTY_PRESETS = {
    "easy": {
        "jitter": (3, 6), "rot": (3, 8), "squeeze": 0.85,
        "blur": (0.2, 0.5), "noise_sigma": 4,
        "bleed_prob": 0.3, "connector_prob": 0.2,
        "scale_y": (0.95, 1.15), "scale_x": (0.9, 1.05),
        "sig_jitter": 10, "sig_rot": 15,
    },
    "medium": {
        "jitter": (6, 10), "rot": (8, 16), "squeeze": 0.70,
        "blur": (0.4, 0.9), "noise_sigma": 6,
        "bleed_prob": 0.5, "connector_prob": 0.4,
        "scale_y": (0.85, 1.3), "scale_x": (0.8, 1.15),
        "sig_jitter": 14, "sig_rot": 20,
    },
    "hard": {
        "jitter": (10, 16), "rot": (14, 24), "squeeze": 0.55,
        "blur": (0.7, 1.6), "noise_sigma": 12,
        "bleed_prob": 0.75, "connector_prob": 0.65,
        "scale_y": (0.7, 1.5), "scale_x": (0.6, 1.3),
        "sig_jitter": 20, "sig_rot": 30,
    },
}
DIFFICULTY_LABELS = {1: "easy", 2: "medium", 3: "hard"}

# ----------------------------------------------------------------------
# FAKE DATA POOLS
def fake_name():
    return fake.name()


EN_DOSAGE_SIGS = [
    "1 tab OD", "1 tab BID", "1 tab TID", "2 tabs BID", "1 cap TID", "1 cap OD",
    "2 puffs PRN", "1 sachet OD", "1 sachet BID", "1 drop TID", "1 tab at night",
    "5 ml BID", "10 ml TID", "1 tab q6h PRN", "2 caps OD", "1 tab BID with meals",
]

def get_random_drug():
    d = random.choice(REAL_DRUGS_DB)
    # English dosage sigs ONLY: the catalog's `dosage` column is Arabic, and the
    # OCR pipeline (and test GT) expects English sigs like "1 cap TID".
    name = d.get('name', 'Unknown')
    dosage = random.choice(EN_DOSAGE_SIGS)
    return f"{name} - {dosage}"

DIAGNOSES = ["Acute pharyngitis", "Type 2 diabetes follow-up", "Hypertension follow-up", "Seasonal allergic rhinitis", "Mild gastritis", "Upper respiratory tract infection", "Lower back pain", "Migraine", "Asthma exacerbation", "Osteoarthritis flare", "Gastroenteritis", "Anemia", "Vitamin D deficiency", "Hypothyroidism", "Hyperlipidemia", "Anxiety disorder", "Depressive episode", "Urinary tract infection", "Otitis media", "Sinusitis", "Bronchitis", "Pneumonia", "Allergic conjunctivitis", "Contact dermatitis", "Eczema", "Psoriasis", "Acne vulgaris", "Gastroesophageal reflux disease", "Peptic ulcer disease", "Irritable bowel syndrome", "Cholelithiasis", "Nephrolithiasis", "Benign prostatic hyperplasia", "Erectile dysfunction", "Dysmenorrhea", "Menorrhagia", "Endometriosis", "Polycystic ovary syndrome", "Menopause symptoms", "Osteoporosis", "Rheumatoid arthritis", "Gout", "Fibromyalgia", "Chronic fatigue syndrome", "Insomnia", "Migraine with aura", "Tension-type headache", "Cluster headache", "Trigeminal neuralgia", "Bell's palsy", "Carpal tunnel syndrome", "Sciatica", "Herniated disc", "Spinal stenosis", "Plantar fasciitis", "Achilles tendinitis", "Tennis elbow", "Golfer's elbow", "Rotator cuff tear", "Frozen shoulder", "Bursitis", "Cellulitis", "Impetigo", "Tinea pedis", "Tinea corporis", "Tinea capitis", "Onychomycosis", "Herpes simplex", "Herpes zoster", "Scabies", "Pediculosis capitis", "Lyme disease", "Malaria", "Dengue fever", "Typhoid fever", "Cholera", "Tuberculosis", "HIV infection", "Hepatitis A", "Hepatitis B", "Hepatitis C", "Syphilis", "Gonorrhea", "Chlamydia infection", "Trichomoniasis", "Candidiasis", "Bacterial vaginosis", "Pelvic inflammatory disease", "Ectopic pregnancy", "Miscarriage", "Preeclampsia", "Gestational diabetes", "Preterm labor", "Postpartum hemorrhage", "Postpartum depression"]


# ----------------------------------------------------------------------
# LOW-LEVEL: draw one "scrawled" line of text onto a transparent layer
# ----------------------------------------------------------------------
def draw_scrawled_text(draw, xy, text, font, base_size,
                        jitter=6, rot_range=9, squeeze=0.85,
                        ink=(20, 20, 130), opacity_range=(140, 235),
                        bleed_prob=0.5, scale_y_range=(0.9, 1.25),
                        scale_x_range=(0.8, 1.1)):
    """
    Draws text character-by-character with random rotation, vertical
    jitter, overlapping spacing, and variable ink opacity, to mimic
    rushed, illegible handwriting.
    """
    x, y = xy
    baseline_wobble = random.uniform(0, 2 * math.pi)

    for i, ch in enumerate(text):
        if ch == " ":
            x += base_size * random.uniform(0.35, 0.55)
            continue

        # per-char randomization
        dy = int(jitter * math.sin(baseline_wobble + i * 0.9) +
                  random.uniform(-jitter * 0.6, jitter * 0.6))
        angle = random.uniform(-rot_range, rot_range)
        opacity = random.randint(*opacity_range)
        scale_y = random.uniform(*scale_y_range)  # tall/short strokes
        scale_x = random.uniform(*scale_x_range)

        # render single glyph to its own small image so we can rotate it
        glyph_img = Image.new("RGBA", (base_size * 2, base_size * 2), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glyph_img)
        gdraw.text((base_size // 2, base_size // 4), ch, font=font,
                   fill=ink + (opacity,))
        glyph_img = glyph_img.resize(
            (max(1, int(base_size * 2 * scale_x)),
             max(1, int(base_size * 2 * scale_y)))
        )
        glyph_img = glyph_img.rotate(angle, resample=Image.BICUBIC, expand=True)

        # extra "shaky pen" pass: draw a second faint offset copy for overlap/ink-bleed
        if random.random() < bleed_prob:
            bleed = Image.new("RGBA", glyph_img.size, (0, 0, 0, 0))
            bdraw = ImageDraw.Draw(bleed)
            bdraw.bitmap((0, 0), glyph_img.split()[-1], fill=ink + (opacity // 3,))
            offx = random.randint(-2, 2)
            offy = random.randint(-2, 2)
            draw._image.paste(bleed, (int(x + offx), int(y + dy + offy)), bleed)

        draw._image.paste(glyph_img, (int(x), int(y + dy)), glyph_img)

        advance = base_size * squeeze * random.uniform(0.55, 0.8)
        x += advance

    return x  # ending x position


def scribble_connector(draw, x1, y1, x2, y2, ink=(20, 20, 130), opacity=90):
    """A wavy connecting line, like a doctor's pen dragging between words."""
    pts = []
    n = 8
    for t in range(n + 1):
        f = t / n
        px = x1 + (x2 - x1) * f
        py = y1 + (y2 - y1) * f + random.uniform(-4, 4)
        pts.append((px, py))
    draw.line(pts, fill=ink + (opacity,), width=random.choice([1, 1, 2]))


# ----------------------------------------------------------------------
# BUILD ONE PRESCRIPTION IMAGE
# ----------------------------------------------------------------------
CLINIC_NAMES = ['Dr. {n} - Internal Medicine Clinic', 'Dr. {n} - Pediatrics Clinic', 'Dr. {n} - Dermatology Center', 'El Nour Medical Center', 'Al Salam Polyclinic']
def render_prescription(idx, difficulty):
    params = DIFFICULTY_PRESETS[difficulty]

    img = Image.new("RGB", (W, H), (250, 248, 240))
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw._image = overlay  # so our helper can .paste on it directly

    doctor = fake_name()
    clinic = random.choice(CLINIC_NAMES).format(n=doctor)
    patient = fake_name()
    age = random.randint(4, 85)
    diag = random.choice(DIAGNOSES)
    date_str = f"{random.randint(1,28):02d}/{random.randint(1,12):02d}/2026"

    header_font = ImageFont.truetype(random.choice(FONT_CANDIDATES), 34)
    printed_font = ImageFont.truetype(PRINTED_FONT_PATH, 22)

    # --- printed clinic header (clean, legible â€” real clinics print this part) ---
    pdraw = ImageDraw.Draw(img)
    pdraw.text((60, 40), clinic, font=header_font, fill=(10, 10, 10))
    pdraw.text((60, 90), "Reg. No: EG-" + str(random.randint(10000, 99999)),
                font=printed_font, fill=(60, 60, 60))
    pdraw.line((60, 130, W - 60, 130), fill=(0, 0, 0), width=2)

    pdraw.text((60, 150), f"Patient: {patient}", font=printed_font, fill=(0, 0, 0))
    pdraw.text((60, 180), f"Age: {age}", font=printed_font, fill=(0, 0, 0))
    pdraw.text((400, 150), f"Date: {date_str}", font=printed_font, fill=(0, 0, 0))
    pdraw.text((60, 210), f"Dx: {diag}", font=printed_font, fill=(0, 0, 0))
    pdraw.line((60, 245, W - 60, 245), fill=(0, 0, 0), width=1)

    # big scrawled Rx symbol
    rx_font = ImageFont.truetype(random.choice(FONT_CANDIDATES), 70)
    draw_scrawled_text(draw, (60, 260), "Rx", rx_font, 70,
                        jitter=params["sig_jitter"] * 0.7,
                        rot_range=params["sig_rot"] * 0.7,
                        bleed_prob=params["bleed_prob"])

    ground_truth_lines = [f"Rx", f"Patient: {patient}", f"Age: {age}",
                          f"Date: {date_str}", f"Dx: {diag}"]
    crop_regions = []

    # --- messy scrawled drug list ---
    y = 350
    n_drugs = random.randint(2, 4)
    chosen = [get_random_drug() for _ in range(n_drugs)]
    body_font_path = random.choice(FONT_CANDIDATES)

    for n_i, drug_str in enumerate(chosen, start=1):
        line = f"{n_i}. {drug_str}"
        ground_truth_lines.append(line)

        size = random.randint(26, 34)
        font = ImageFont.truetype(body_font_path, size)

        x = 70
        end_x = draw_scrawled_text(
            draw, (x, y), line, font, size,
            jitter=random.randint(*params["jitter"]),
            rot_range=random.randint(*params["rot"]),
            squeeze=params["squeeze"],
            bleed_prob=params["bleed_prob"],
            scale_y_range=params["scale_y"],
            scale_x_range=params["scale_x"],
        )
        # occasional connecting scribble to next line (like doctor's underline/strike)
        if random.random() < params["connector_prob"]:
            scribble_connector(draw, x + 10, y + size + 6, end_x - 30, y + size + 6)

        margin = 15
        crop_regions.append({"box": (int(70 - margin), int(y - margin), int(end_x + margin), int(y + size + margin + 10)), "text": line})

        y += size + random.randint(28, 46)

    # signature scrawl at bottom (illegible loops, not real text)
    sig_font = ImageFont.truetype(random.choice(FONT_CANDIDATES), 40)
    fake_sig_chars = "".join(random.choice("~^-_/\\") for _ in range(12))
    draw_scrawled_text(draw, (650, H - 160), fake_sig_chars, sig_font, 40,
                        jitter=params["sig_jitter"], rot_range=params["sig_rot"],
                        ink=(10, 10, 90), bleed_prob=params["bleed_prob"])
    pdraw.text((650, H - 110), "Doctor's signature & stamp",
               font=printed_font, fill=(90, 90, 90))
    ground_truth_lines.append(f"Signed: {doctor}")

    # --- composite scrawl overlay onto base image ---
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # --- global degradation to feel like a scanned/photographed paper ---
    img = apply_paper_degradation(img, params)

    fname = f"messy_rx_{idx:03d}.png"
    fpath = os.path.join(IMG_DIR, fname)
    img.save(fpath, "PNG")

    cropped_data = []
    for i, reg in enumerate(crop_regions):
        crop_name = f"line_crop_{idx:03d}_{i}.png"
        crop_path = os.path.join(CROP_DIR, crop_name)
        cimg = img.crop(reg["box"])
        cimg.save(crop_path, "PNG")
        cropped_data.append({"file": crop_name, "text": reg["text"], "source_rx": fname})

    return {
        "file": fname,
        "difficulty": difficulty,
        "ground_truth_text": ground_truth_lines,
        "doctor": doctor,
        "patient": patient,
        "note": "SYNTHETIC / FAKE DATA — for OCR training only",
        "cropped_data": cropped_data
    }


def apply_paper_degradation(img, params):
    # slight rotation like a photographed page
    angle = random.uniform(-1.5, 1.5)
    img = img.rotate(angle, resample=Image.BICUBIC, fillcolor=(250, 248, 240))

    # paper grain noise
    import numpy as np
    arr = np.array(img).astype(np.int16)
    noise = np.random.normal(0, params["noise_sigma"], arr.shape).astype(np.int16)
    arr = np.clip(arr + noise, 0, 255).astype("uint8")
    img = Image.fromarray(arr)

    # mild blur to simulate ink bleed / camera softness
    img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(*params["blur"])))

    # vignette-ish contrast tweak
    img = ImageOps.autocontrast(img, cutoff=1)
    return img


# ----------------------------------------------------------------------
# INTERACTIVE PROMPTS
# ----------------------------------------------------------------------
def ask_num_images():
    while True:
        raw = input("ÙƒØ§Ù… ØµÙˆØ±Ø© Ø¹Ø§ÙŠØ² ØªÙˆÙ„Ù‘Ø¯ØŸ (Ø§ÙƒØªØ¨ Ø±Ù‚Ù…): ").strip()
        if raw.isdigit() and int(raw) > 0:
            return int(raw)
        print("Ù…Ù† ÙØ¶Ù„Ùƒ Ø§ÙƒØªØ¨ Ø±Ù‚Ù… ØµØ­ÙŠØ­ Ø£ÙƒØ¨Ø± Ù…Ù† ØµÙØ±.")


def ask_difficulty():
    print("Ø§Ø®ØªØ§Ø± Ù…Ø³ØªÙˆÙ‰ Ø§Ù„ØµØ¹ÙˆØ¨Ø©:")
    print("  1) Ø³Ù‡Ù„   (easy)")
    print("  2) Ù…ØªÙˆØ³Ø· (medium)")
    print("  3) ØµØ¹Ø¨   (hard)")
    print("  4) Ù…Ø®ØªÙ„Ø· Ø¹Ø´ÙˆØ§Ø¦ÙŠ (ÙŠÙˆØ²Ø¹ Ø§Ù„ØµÙˆØ± Ø¹Ù„Ù‰ Ø§Ù„Ø«Ù„Ø§Ø« Ù…Ø³ØªÙˆÙŠØ§Øª)")
    while True:
        raw = input("Ø§ÙƒØªØ¨ Ø±Ù‚Ù… (1-4): ").strip()
        if raw in {"1", "2", "3", "4"}:
            return int(raw)
        print("Ù…Ù† ÙØ¶Ù„Ùƒ Ø§Ø®ØªØ§Ø± Ø±Ù‚Ù… Ù…Ù† 1 Ù„Ù€ 4.")


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

# ============== تشغيل التوليد (متسلسل بدقة البذور) ==============
records, all_crops = [], []
DIFFS = ["easy", "medium", "hard"]
_GEN_DONE = os.path.exists(os.path.join(GEN_OUT, "line_ground_truth.json"))
if _GEN_DONE:
    print("data already generated — skipping ✓")
    all_crops = json.load(open(os.path.join(GEN_OUT, "line_ground_truth.json"), encoding="utf-8"))
for i in range(1 if not _GEN_DONE else 0, GEN_PAGES + 1 if not _GEN_DONE else 0):
    random.seed(GEN_SEED + i)
    fake.seed_instance(GEN_SEED + i)
    rec = render_prescription(i, DIFFS[i % 3])
    records.append(rec)
    all_crops.extend(rec.get("cropped_data", []))
    if i % 250 == 0:
        print("  " + str(i) + "/" + str(GEN_PAGES))

if not _GEN_DONE:
    json.dump(records, open(os.path.join(GEN_OUT, "ground_truth.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(all_crops, open(os.path.join(GEN_OUT, "line_ground_truth.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("generated: " + str(len(records)) + " pages / " + str(len(all_crops)) + " crops")

# ============== 2) الـholdout المجمد من Drive ==============
print("=== 2/5 الـholdout من Drive ===")
import os as _os
if not _os.path.exists("/content/drive/MyDrive"):
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
        img = Image.open(os.path.join(CROP_DIR, e["file"])).convert("RGB")
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
