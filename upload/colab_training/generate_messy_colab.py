CLINIC_NAMES = ["Dr. {n} - Internal Medicine Clinic",
                "Dr. {n} - Pediatrics Clinic",
                "Dr. {n} - Dermatology Center",
                "El Nour Medical Center",
                "Al Salam Polyclinic"]
"""
Synthetic MESSY-HANDWRITING prescription generator
----------------------------------------------------
Purpose: produce FAKE prescription images with deliberately hard-to-read,
doctor-style scrawl, for training/testing OCR models on illegible text.

NOTHING here is real patient / doctor data â€” every name, diagnosis and
doctor is randomly assembled from generic word lists.

Illegibility is achieved purely through geometric distortion of ordinary
system fonts (per-character jitter, rotation, shear, baseline wobble,
stroke overlap, ink bleed, variable pressure/opacity, connecting
scribble-lines between words) â€” no handwriting fonts are needed.

Output: PNG images + a JSON file with the GROUND-TRUTH text (and the
difficulty tier) for each image â€” essential for OCR training/eval.

Run it and answer the two prompts:
    1) How many images to generate
    2) Difficulty level: 1 = easy, 2 = medium, 3 = hard
"""

import os
import json
import random
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from faker import Faker

fake = Faker('en_US')

with open('real_drugs.json', 'r', encoding='utf-8') as f:
    REAL_DRUGS_DB = json.load(f)
with open('generic_drugs.json', 'r', encoding='utf-8') as f:
    _GEN = json.load(f)
REAL_DRUGS_DB = list(REAL_DRUGS_DB) + [{"drug_id": f"gen{i}", "name": n.title()} for i, n in enumerate(_GEN)]


# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
OUT_DIR = os.environ.get("GEN_OUT", "messy_rx_dataset")
IMG_DIR = os.path.join(OUT_DIR, "images")
CROP_DIR = os.path.join(OUT_DIR, "line_crops")
os.makedirs(CROP_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

W, H = 1000, 1300

FONT_CANDIDATES = [
    "fonts/ariali.ttf", "fonts/timesi.ttf", "fonts/calibrii.ttf",
    "fonts/georgiai.ttf", "fonts/trebucit.ttf", "fonts/comic.ttf",
]
PRINTED_FONT_PATH = "fonts/arial.ttf"

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
def _render_worker(args):
    i, seed0, difficulty = args
    random.seed(seed0 + i)
    fake.seed_instance(seed0 + i)
    rec = render_prescription(i, difficulty)
    return rec, rec.get("cropped_data", [])


def main():
    import multiprocessing as mp
    n = int(os.environ.get("GEN_PAGES", "2000"))
    seed0 = int(os.environ.get("GEN_SEED", "60001"))
    records, all_crops = [], []
    diffs = ["easy", "medium", "hard"]
    jobs = [(i, seed0, diffs[i % 3]) for i in range(1, n + 1)]
    with mp.Pool(2) as pool:
        for k, (rec, crops) in enumerate(pool.imap_unordered(_render_worker, jobs), 1):
            records.append(rec); all_crops.extend(crops)
            if k % 200 == 0: print(f"  {k}/{n}")
    json.dump(records, open(os.path.join(OUT_DIR, "ground_truth.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(all_crops, open(os.path.join(OUT_DIR, "line_ground_truth.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"DONE: {n} pages / {len(all_crops)} crops -> {OUT_DIR}")


if __name__ == "__main__":
    main()