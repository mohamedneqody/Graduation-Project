import os
import re
import json
import io
import base64
import hashlib
import torch
import numpy as np
from PIL import Image
import cv2
from difflib import SequenceMatcher
from transformers import (
    AutoProcessor,
    AutoModelForCausalLM,
    DeiTImageProcessor,
    RobertaTokenizer,
    TrOCRProcessor,
    VisionEncoderDecoderModel
)

from ocr_config import settings as ocr_settings
from ocr_image_prep import (
    apply_exif_orientation,
    deskew_pil,
    enhance_for_recognition,
    ink_x_bounds,
    invert_letterbox_box,
    letterbox_square,
    pad_left_white,
    prepare_trocr_crop,
    split_oversized_bands,
)
from ocr_scoring import agreement_ratio
from ocr_scoring import fuse_ocr_hypotheses as _fuse_rule
from ocr_scoring import geo_mean_confidence
from ocr_scoring import catalog_score as _catalog_score

class PrescriptionOCREngine:
    def __init__(self, model_dir=None, drugs_db_path=None, device=None):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        # 1. Model Path (OCR_MODEL_DIR enables A/B of candidate checkpoints
        # without touching the deployed one)
        if model_dir is None:
            model_dir = os.environ.get("OCR_MODEL_DIR") or os.path.join(self.base_dir, "trocr-finetuned-final")
        self.model_dir = model_dir

        # 2. Device Selection: TrOCR moves to CUDA (fp16) for recognition,
        # while Florence-2 stays on CPU by default to preserve VRAM on the 4GB
        # T1200 (FLORENCE_DEVICE=cuda opts in when headroom exists).
        if device is None:
            self.trocr_device = "cuda" if torch.cuda.is_available() else "cpu"
            self.florence_device = ocr_settings.florence_device
        else:
            self.trocr_device = device
            self.florence_device = ocr_settings.florence_device
        if self.florence_device not in ("cpu", "cuda"):
            self.florence_device = "cpu"
        if self.florence_device == "cuda" and not torch.cuda.is_available():
            self.florence_device = "cpu"

        self.device = self.trocr_device
        print(f"[OCR Engine] Initializing TrOCR from '{self.model_dir}' on {self.trocr_device.upper()} (Florence-2 on {self.florence_device.upper()})...")
        
        # 3. Load TrOCR Processor and Model
        self.image_processor = DeiTImageProcessor.from_pretrained(
            self.model_dir, 
            do_center_crop=False, 
            size={"height": 384, "width": 384}
        )
        self.tokenizer = RobertaTokenizer.from_pretrained(self.model_dir)
        self.processor = TrOCRProcessor(image_processor=self.image_processor, tokenizer=self.tokenizer)
        self.model = VisionEncoderDecoderModel.from_pretrained(self.model_dir).to(self.trocr_device)
        if self.trocr_device == "cuda":
            self.model = self.model.half()
        self.model.eval()
        
        # 4. Load Real Drugs Database for Fuzzy Matching
        if drugs_db_path is None:
            drugs_db_path = os.path.join(self.base_dir, "real_drugs.json")
        self.drugs_db_path = drugs_db_path
        
        self.drugs_db = []
        if os.path.exists(self.drugs_db_path):
            with open(self.drugs_db_path, "r", encoding="utf-8") as f:
                self.drugs_db = json.load(f)
            print(f"[OCR Engine] Loaded {len(self.drugs_db)} medications into knowledge base.")
        else:
            print(f"[OCR Engine] Warning: Drugs database not found at '{self.drugs_db_path}'")

        # 5. Florence-2 Vision & Layout Engine
        self.florence_model_id = "microsoft/Florence-2-base-ft"
        self.florence_processor = None
        self.florence_model = None

    def load_florence(self):
        if self.florence_model is None:
            print("[OCR Engine] Initializing Florence-2 Vision & Layout Engine from D:\\huggingface_cache...")
            self.florence_processor = AutoProcessor.from_pretrained(
                self.florence_model_id,
                trust_remote_code=True
            )
            self.florence_model = AutoModelForCausalLM.from_pretrained(
                self.florence_model_id,
                trust_remote_code=True,
                torch_dtype=torch.float32 if self.florence_device == "cpu" else torch.float16
            ).to(self.florence_device)
            self.florence_model.eval()
            print(f"[OCR Engine] Florence-2 Vision Engine initialized successfully on {self.florence_device.upper()}.")

    def _preprocess_crop(self, image):
        """Aspect-ratio-preserving preprocessing for one line crop.

        The legacy pipeline let the processor squash every crop to 384x384,
        destroying glyph geometry on wide lines (1500x90 -> 384x384). We now
        optionally upscale tiny ink and letterbox onto a white square first,
        so the fixed 384x384 encoder resize no longer distorts handwriting.
        """
        if isinstance(image, str):
            img = Image.open(image).convert("RGB")
        elif isinstance(image, Image.Image):
            img = image.convert("RGB")
        elif isinstance(image, np.ndarray):
            img = Image.fromarray(image).convert("RGB")
        else:
            raise ValueError("Unsupported image input format.")
        return prepare_trocr_crop(
            img,
            input_size=ocr_settings.trocr_input_size,
            letterbox=ocr_settings.trocr_letterbox,
            min_text_height=ocr_settings.min_text_height_px,
            min_content_h=ocr_settings.trocr_min_content_h,
            max_upscale=ocr_settings.max_upscale,
        )

    def _trocr_generate(self, pixel_values):
        """Beam-search decode with KV cache and real sequence confidence.

        use_cache=True is critical: the shipped generation_config.json has
        use_cache=false, which re-runs the whole decoder every token and made
        decoding ~10x slower on the T1200. return_dict_in_generate exposes
        sequences_scores (length-normalized cumulative log-prob) for honest
        confidence instead of the old hardcoded 0.88/0.92/0.95 constants.
        """
        with torch.inference_mode():
            output = self.model.generate(
                pixel_values,
                max_length=24,                             # was 64 — drug name+strength rarely exceeds 20 chars; 64 allowed hallucinated tails
                num_beams=ocr_settings.trocr_num_beams,
                decoder_start_token_id=self.tokenizer.cls_token_id,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.sep_token_id,
                no_repeat_ngram_size=2,                    # was 3 — stricter: no repeated bigrams
                early_stopping=True,
                length_penalty=0.6,                        # NEW: penalise long outputs (prefer shorter, confident readings)
                repetition_penalty=ocr_settings.trocr_repetition_penalty,  # stops token / mode collapse repetition
                use_cache=True,
                return_dict_in_generate=True,
                output_scores=True,
            )
        return output

    def _decode_batch(self, pixel_values):
        output = self._trocr_generate(pixel_values)
        texts = self.processor.batch_decode(output.sequences, skip_special_tokens=True)
        seqs = output.sequences
        seq_scores = getattr(output, "sequences_scores", None)
        pad_id = self.tokenizer.pad_token_id
        results = []
        for i, text in enumerate(texts):
            n_tokens = int((seqs[i] != pad_id).sum().item())
            score = float(seq_scores[i].item()) if seq_scores is not None else None
            results.append({
                "text": text.strip(),
                "confidence": geo_mean_confidence(score, n_tokens),
            })
        return results

    def read_line_crop(self, image_input):
        """
        Takes a PIL Image or image path of a line crop and returns a dict:
        {"text": recognized text, "confidence": geometric-mean token prob}.
        """
        img = self._preprocess_crop(image_input)
        pixel_values = self.processor(img, return_tensors="pt").pixel_values.to(self.trocr_device)
        if self.trocr_device == "cuda":
            pixel_values = pixel_values.half()
        return self._decode_batch(pixel_values)[0]

    def read_line_crops_batch(self, images_list):
        """
        Takes a list of PIL Images (or crops) and decodes all lines in
        bounded micro-batches (TROCR_BATCH_SIZE) to keep 4GB VRAM safe.
        Returns a list of {"text", "confidence"} dicts with 100% identical
        accuracy to sequential decoding.
        """
        if not images_list:
            return []

        prepped = [self._preprocess_crop(img) for img in images_list]
        results = []
        batch_size = max(1, ocr_settings.trocr_batch_size)
        for start in range(0, len(prepped), batch_size):
            chunk = prepped[start:start + batch_size]
            pixel_values = self.processor(chunk, return_tensors="pt").pixel_values.to(self.trocr_device)
            if self.trocr_device == "cuda":
                pixel_values = pixel_values.half()
            results.extend(self._decode_batch(pixel_values))
        return results

    def segment_lines(self, full_image):
        """
        Adaptive line segmentation using adaptive thresholding, wavy separator line removal,
        and horizontal projection profile.
        Expects an ALREADY-deskewed image (see process_prescription): a tilted page makes
        the projection profile merge/split text bands. Binarization is used ONLY for the
        segmentation mask — the returned crops come from the color image.
        Returns a list of PIL Image crops representing true text lines.
        """
        if isinstance(full_image, str):
            with open(full_image, 'rb') as f:
                img_bytes = f.read()
            cv_img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        elif isinstance(full_image, Image.Image):
            cv_img = cv2.cvtColor(np.array(full_image), cv2.COLOR_RGB2BGR)
        elif isinstance(full_image, np.ndarray):
            cv_img = full_image
        else:
            raise ValueError("Unsupported image input format.")

        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # Detect structural divider lines (e.g., under doctor header, above footer)
        _, bin_inv = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY_INV)
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        lines_morph = cv2.morphologyEx(bin_inv, cv2.MORPH_OPEN, h_kernel, iterations=2)
        cnts, _ = cv2.findContours(lines_morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Focus on the prescription body. Divider lines no longer blind-crop
        # the body: a thin handwritten stroke inside the top-25% window used
        # to be mistaken for a header divider (top_crop jumped deep and
        # swallowed real medication lines). Bands are detected on the FULL
        # body first, then pruned against validated printed rules only.
        body_top, body_bottom = int(h * 0.05), int(h * 0.95)
        body = gray[body_top:body_bottom, int(w * 0.05):int(w * 0.95)]

        # Adaptive thresholding handles varying illumination
        thresh = cv2.adaptiveThreshold(body, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 41, 15)

        # 1. Filter out wavy horizontal separator lines and scribble rules
        # Separator strokes are very wide (> 30% of body width) but thin (< 32px height)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cleaned_thresh = thresh.copy()
        for cnt in contours:
            cx, cy, cw, ch = cv2.boundingRect(cnt)
            if cw > (body.shape[1] * 0.30) and ch < 32:
                cv2.drawContours(cleaned_thresh, [cnt], -1, 0, -1)

        # 2. Gaussian blur connects characters horizontally into solid text bands
        blurred = cv2.GaussianBlur(cleaned_thresh, (61, 15), 0)
        _, thresh2 = cv2.threshold(blurred, 40, 255, cv2.THRESH_BINARY)

        # 3. Horizontal projection profile
        hist = np.sum(thresh2, axis=1)
        smoothed_hist = np.convolve(hist, np.ones(15)/15, mode='same')
        threshold_val = np.max(smoothed_hist) * 0.05 if np.max(smoothed_hist) > 0 else 1

        raw_lines = []
        in_line = False
        start_y = 0
        min_line_height = 28

        for y, val in enumerate(smoothed_hist):
            if val > threshold_val and not in_line:
                in_line = True
                start_y = y
            elif val <= threshold_val and in_line:
                in_line = False
                end_y = y
                if (end_y - start_y) >= min_line_height:
                    y1 = max(0, start_y - 10)
                    y2 = min(body_bottom - body_top, end_y + 10)
                    raw_lines.append((y1, y2))

        # 4. Merge vertically overlapping line bands (body coordinates)
        merged_lines = []
        for l in raw_lines:
            if not merged_lines:
                merged_lines.append(l)
            else:
                prev_y1, prev_y2 = merged_lines[-1]
                curr_y1, curr_y2 = l
                if curr_y1 < prev_y2:
                    merged_lines[-1] = (prev_y1, max(prev_y2, curr_y2))
                else:
                    merged_lines.append(l)

        # 5. Prune header/footer bands against validated printed rules.
        # Printed rules are long, straight and very thin (ch < 12); handwriting
        # is not, so medication lines are never mistaken for dividers. Bands
        # ENTIRELY above the lowest header rule (or below the highest footer
        # rule) are dropped; content is never cut mid-line.
        header_dividers = [cv2.boundingRect(c)[1] + cv2.boundingRect(c)[3] for c in cnts
                           if cv2.boundingRect(c)[2] > (w * 0.40) and cv2.boundingRect(c)[3] < 12 and cv2.boundingRect(c)[1] < (h * 0.20)]
        footer_dividers = [cv2.boundingRect(c)[1] for c in cnts
                           if cv2.boundingRect(c)[2] > (w * 0.40) and cv2.boundingRect(c)[3] < 15 and cv2.boundingRect(c)[1] > (h * 0.80)]
        if header_dividers:
            cut = max(header_dividers) + 4 - body_top
            kept = [b for b in merged_lines if b[1] > cut]
            if kept:
                merged_lines = kept
        if footer_dividers:
            cut = min(footer_dividers) - 4 - body_top
            kept = [b for b in merged_lines if b[0] < cut]
            if kept:
                merged_lines = kept

        # 6. Split oversized merged bands at their deepest internal valley:
        # tightly-spaced handwritten lines otherwise merge into one band and
        # several medications get decoded as a single line. (Profile and bands
        # are both in body coordinates here.)
        merged_lines = split_oversized_bands(merged_lines, smoothed_hist)

        # Body x-window: the ink-bbox crop below is computed inside these
        # margins (same idea as the old fixed 5%-95% strip) but the crop
        # itself follows the line's real ink extent, so word starts/ends are
        # never cut and blank margins never reach the recognizer.
        body_x1, body_x2 = int(w * 0.03), int(w * 0.97)

        line_crops = []
        MIN_BAND_PX = 45  # thinner than this = ascender/descender sliver, not a line
        for (y1, y2) in merged_lines:
            if (y2 - y1) < MIN_BAND_PX:
                continue
            y1_page, y2_page = y1 + body_top, y2 + body_top
            band = cv_img[y1_page:y2_page, body_x1:body_x2]

            bounds = ink_x_bounds(band)
            if bounds is None:
                continue
            bx0, bx1 = bounds
            ink_w = bx1 - bx0
            # Filter out isolated standalone marks/logos (like Rx symbol or
            # stray dots) that don't span medication text width.
            if ink_w < min(60, int(band.shape[1] * 0.15)):
                continue

            pad_x = max(ocr_settings.crop_pad_px, int(ink_w * ocr_settings.crop_pad_x_ratio))
            # LEFT-biased margin: the first glyph is the decoder's weakest
            # region, so it gets extra runway (fixes "Diovan" -> "ovan"-style
            # dropped first characters at the source).
            pad_x_left = int(pad_x * (1.0 + ocr_settings.crop_pad_left_ratio))
            pad_y = max(ocr_settings.crop_pad_px, int((y2_page - y1_page) * ocr_settings.crop_pad_y_ratio))
            cx1 = max(body_x1, body_x1 + bx0 - pad_x_left)
            cx2 = min(body_x2, body_x1 + bx1 + pad_x)
            cy1 = max(0, y1_page - pad_y)
            cy2 = min(h, y2_page + pad_y)

            crop = cv_img[cy1:cy2, cx1:cx2]
            crop_pil = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            line_crops.append({
                "image": crop_pil,
                "bbox": [cy1, cx1, cy2, cx2]
            })

        if not line_crops:
            return [{"image": Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)), "bbox": [0, 0, h, w]}]

        return line_crops

    def segment_lines_florence(self, full_image, raw_bytes=None):
        """
        AI Vision-Based Prescription Line Segmentation & Bounding Box Extraction via Florence-2.
        Extracts pixel-accurate bounding boxes for medication lines and filters out headers/symbols.

        The page is LETTERBOXED onto the Florence canvas (aspect-preserving) instead of being
        squashed to 768x768 — the old squash destroyed handwriting stroke geometry and made
        <OCR_WITH_REGION> return empty lists. Detected boxes are mapped back to original image
        coordinates. Florence always receives the natural (never binarized) image. A page-level
        generation confidence (from the beam-search sequence score) is attached to every crop.
        """
        self.load_florence()
        if isinstance(full_image, str):
            with open(full_image, "rb") as rf:
                raw_bytes = rf.read()
            full_image = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        elif isinstance(full_image, np.ndarray):
            full_image = Image.fromarray(cv2.cvtColor(full_image, cv2.COLOR_BGR2RGB))
        elif isinstance(full_image, Image.Image):
            full_image = full_image.convert("RGB")
        else:
            raise ValueError("Unsupported image input format.")

        orig_w, orig_h = full_image.size

        # Checkpoint 2 SHA256 Hash Calculation (io/hashlib are module-level imports;
        # the old function-local `import io` shadowed the module and crashed the
        # string-path branch with UnboundLocalError).
        if raw_bytes:
            img_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        else:
            buf = io.BytesIO()
            full_image.save(buf, format="PNG")
            img_sha256 = hashlib.sha256(buf.getvalue()).hexdigest()

        print(f"\n[PIPELINE AUDIT - Checkpoint 2: Florence-2 Segmentation] Image size: {orig_w}x{orig_h} | SHA256: {img_sha256}")

        prompt = "<OCR_WITH_REGION>"
        # Aspect-preserving letterbox onto the canvas (no distortion).
        lb = letterbox_square(full_image, ocr_settings.florence_canvas)
        inputs = self.florence_processor(text=prompt, images=lb.image, return_tensors="pt").to(self.florence_device)

        with torch.inference_mode():
            output = self.florence_model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=ocr_settings.florence_max_new_tokens,
                num_beams=ocr_settings.florence_num_beams,
                do_sample=False,
                use_cache=True,
                return_dict_in_generate=True,
                output_scores=True,   # required for sequences_scores in HF 4.4x
            )

        # Page-level confidence from the real beam score. Florence does not
        # expose per-label probabilities; every label inherits this honest
        # page-level evidence value (never a fabricated constant).
        page_conf = 0.0
        seq_scores = getattr(output, "sequences_scores", None)
        if seq_scores is not None:
            pad_id = getattr(self.florence_processor.tokenizer, "pad_token_id", None)
            if pad_id is not None:
                n_tok = int((output.sequences[0] != pad_id).sum().item())
            else:
                n_tok = int(output.sequences.shape[1])
            page_conf = geo_mean_confidence(float(seq_scores[0].item()), n_tok)
        print(f"[OCR Engine] Florence page confidence: {page_conf:.3f}")

        generated_text = self.florence_processor.batch_decode(output.sequences, skip_special_tokens=False)[0]
        # Boxes come back in letterboxed-canvas space; image_size must match
        # what the model actually saw. They are mapped back to original space
        # right after extraction.
        parsed_answer = self.florence_processor.post_process_generation(
            generated_text,
            task=prompt,
            image_size=(ocr_settings.florence_canvas, ocr_settings.florence_canvas)
        )

        ocr_data = parsed_answer.get("<OCR_WITH_REGION>", {})
        labels = ocr_data.get("labels", [])
        quad_boxes = ocr_data.get("quad_boxes", [])
        bboxes = ocr_data.get("bboxes", [])

        crops_data = []
        excluded_header_lines = []; excluded_header_bboxes = []
        for i, label in enumerate(labels):
            clean_label = label.replace("</s>", "").strip()

            # Extract (and un-letterbox) the box FIRST so every exclusion
            # branch can register the region in excluded_header_bboxes — the
            # OpenCV path uses those regions to drop header crops. (This list
            # was never populated before, so header text leaked into TrOCR as
            # phantom medication lines.)
            box = None
            if i < len(quad_boxes):
                q = quad_boxes[i]
                box = [min(q[0], q[6]), min(q[1], q[3]), max(q[2], q[4]), max(q[5], q[7])]
            elif i < len(bboxes):
                box = bboxes[i]
            if box is not None:
                box = invert_letterbox_box(box, lb, orig_w, orig_h)

            def _exclude(reason: str) -> None:
                excluded_header_lines.append(f"{clean_label} ({reason})")
                if box is not None:
                    excluded_header_bboxes.append([int(round(v)) for v in box])

            # 1. Filter out clinic pad headers, doctor titles, patient info, registration, phones, specialties
            is_header = any(h in clean_label.lower() for h in [
                "clinic", "hospital", "medical center", "medical centre", "center", "centre", "polyclinic", "prescription", "dr.", "dr ", "dr:", "dx:", "doctor", "consultant", "specialist",
                "internal medicine", "pediatric", "surgery", "cardiology",
                "tel:", "phone", "patient", "name:", "age:", "date:", "address", "reg.", "reg:"
            ])
            if is_header:
                _exclude("Clinic/Doctor/Patient Header")
                continue

            # Check for diagnosis prefixes or common clinical disease conditions (v3.0-strict Rule 1)
            is_diagnosis = (
                bool(re.search(r'^\s*(d[x\:\.]|diag|diagnosis)\b', clean_label, re.IGNORECASE)) or
                any(cond in clean_label.lower() for cond in [
                    "rhinitis", "pharyngitis", "hypertension", "diabetes", "gastritis",
                    "migraine", "asthma", "allergy", "allergic", "seasonallah", "bronchitis",
                    "tonsillitis", "sinusitis", "urticaria", "dermatitis", "pain", "back pain", "complaint"
                ])
            )
            if is_diagnosis:
                _exclude("Diagnosis/Condition Line")
                continue

            if clean_label.lower() in ["rx", "℞"]:
                _exclude("Rx Symbol")
                continue

            if len(clean_label) < 2:
                continue

            # 2. Filter out standalone pack count or dosage form without a drug name (e.g. '20 Capsules')
            if re.match(r'^\d+\s*(capsules?|tabs?|tablets?|caps?|ml|pills?|sachets?|vials?|ampoules?)$', clean_label, re.IGNORECASE):
                _exclude("Standalone packaging info")
                continue

            if box:
                x1, y1, x2, y2 = [int(v) for v in box]

                # Rule A: Exclude signature / stamp / footer area
                # Never exclude if the line contains medication patterns (strength, dosage forms, units, frequencies)
                has_med_pattern = bool(re.search(r'(\d+\s*(?:mg|g|mcg|ml|iu|%|tabs?|caps?|tablets?|capsules?|vials?|ampoules?|tds|bid|od|tid)|\b(tab|tabs|caps|cap|mg|ml|syrup|ointment)\b)', clean_label, re.IGNORECASE))
                is_known_drug = any(d.get("name", "").split()[0].lower() in clean_label.lower().split() for d in self.drugs_db if len(d.get("name", "")) > 3)
                if is_known_drug:
                    has_med_pattern = True
                is_signature_keyword = any(k in clean_label.lower() for k in ["signature", "signed", "doctor", "dr.", "stamp", "license", "address", "phone", "tel:"])

                if y1 > orig_h * 0.92:
                    if not has_med_pattern or is_signature_keyword:
                        _exclude("Doctor Signature / Footer Zone")
                        continue

                # Rule B: Ignore tiny speck boxes
                if (x2 - x1) < 25 or (y2 - y1) < 15:
                    continue

                crops_data.append({
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "label": clean_label
                })

        # Merge boxes that belong to the same text line (centers within 25px or high vertical overlap)
        crops_data.sort(key=lambda b: (b["y1"] + b["y2"]) / 2)
        merged_boxes = []
        for b in crops_data:
            b_center_y = (b["y1"] + b["y2"]) / 2
            b_h = b["y2"] - b["y1"]
            merged = False
            for mb in merged_boxes:
                mb_center_y = (mb["y1"] + mb["y2"]) / 2
                mb_h = mb["y2"] - mb["y1"]
                overlap_y = min(b["y2"], mb["y2"]) - max(b["y1"], mb["y1"])
                if overlap_y > 0.4 * min(b_h, mb_h) or abs(b_center_y - mb_center_y) < 25:
                    mb["x1"] = min(mb["x1"], b["x1"])
                    mb["y1"] = min(mb["y1"], b["y1"])
                    mb["x2"] = max(mb["x2"], b["x2"])
                    mb["y2"] = max(mb["y2"], b["y2"])
                    mb["label"] = f"{mb['label']} {b['label']}".strip()
                    merged = True
                    break
            if not merged:
                merged_boxes.append(b)

        final_crops = []
        for mb in merged_boxes:
            x1, y1, x2, y2 = mb["x1"], mb["y1"], mb["x2"], mb["y2"]
            pad_x = int((x2 - x1) * 0.05) + 25
            pad_y = int((y2 - y1) * 0.15) + 8
            crop_x1 = max(0, x1 - pad_x)
            crop_y1 = max(0, y1 - pad_y)
            crop_x2 = min(orig_w, x2 + pad_x)
            crop_y2 = min(orig_h, y2 + pad_y)

            crop_img = full_image.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            final_crops.append({
                "image": crop_img,
                "bbox": [crop_y1, crop_x1, crop_y2, crop_x2],
                "florence_text": mb["label"],
                "florence_conf": page_conf,
            })

        # Sort lines top-to-bottom
        final_crops.sort(key=lambda c: c["bbox"][0])

        # Construct image_fingerprint for diagnosis & verification
        orientation = "landscape" if orig_w > orig_h else "portrait"
        
        box_items = []
        for i, label in enumerate(labels):
            box = None
            if i < len(quad_boxes):
                q = quad_boxes[i]
                box = [min(q[0], q[6]), min(q[1], q[3]), max(q[2], q[4]), max(q[5], q[7])]
            elif i < len(bboxes):
                box = bboxes[i]
            if box:
                box = invert_letterbox_box(box, lb, orig_w, orig_h)
                clean_l = label.replace("</s>", "").strip()
                if clean_l:
                    box_items.append({"text": clean_l, "y": box[1], "x": box[0]})
        
        box_items.sort(key=lambda item: (item["y"], item["x"]))
        
        # 1. top_left_visible_text: first 5-8 words in upper area
        top_words = []
        for item in box_items[:3]:
            top_words.extend(item["text"].split())
        top_left_text = " ".join(top_words[:8]) if top_words else "None"
        
        # 2. clinic_name_guess:
        clinic_guess = "Unknown"
        for item in box_items:
            t_low = item["text"].lower()
            if any(k in t_low for k in ["clinic", "hospital", "dr.", "dr ", "dr:", "doctor", "consultant", "center", "polyclinic"]):
                clinic_guess = item["text"]
                break
        if clinic_guess == "Unknown" and box_items:
            clinic_guess = box_items[0]["text"]
            
        # 3. patient_name_guess:
        patient_guess = "Unknown"
        for item in box_items:
            t_low = item["text"].lower()
            if any(k in t_low for k in ["patient", "pt:", "name:", "age:"]):
                patient_guess = item["text"]
                break
                
        image_fingerprint = {
            "sha256": img_sha256,
            "top_left_visible_text": top_left_text,
            "clinic_name_guess": clinic_guess,
            "patient_name_guess": patient_guess,
            "approximate_image_orientation": orientation,
            "number_of_handwritten_lines_visible": len(final_crops)
        }

        return final_crops, excluded_header_lines, image_fingerprint, excluded_header_bboxes

    def fuse_ocr_hypotheses(self, clean_trocr: str, clean_florence: str,
                            trocr_conf: float = 0.0, florence_conf: float = 0.0) -> tuple[str, str, float, bool]:
        """
        Evidence-Based Multi-Model Fusion (v4.1):
        Balances Florence-2 (Printed Fonts & Layout) with TrOCR (Cursive Handwriting)
        using REAL model confidences, text agreement, and drug-catalog evidence.
        Returns: (chosen_raw, visual_style, ocr_confidence, is_model_disagreement)

        Rules (see ocr_scoring.fuse_ocr_hypotheses):
          - The chosen text is always one of the two inputs (never invented).
          - Agreement between the two models boosts confidence (capped 0.97).
          - Disagreement caps confidence at 0.70 and sets model_disagreement,
            which the backend traffic light turns into a mandatory review.
        The old hardcoded constants (0.88/0.92/0.95/0.97) are gone: ocr_confidence
        is now derived from decoder log-probabilities.
        """
        catalog_names = [d.get("name", "") for d in self.drugs_db if d.get("name")] if self.drugs_db else []
        return _fuse_rule(clean_trocr, clean_florence, trocr_conf, florence_conf, catalog_names)

    def _retry_weak_lines(self, crops_images, decoded, florence_texts=None):
        """
        Second-opinion pass for weak lines: re-decode each low-confidence crop
        with a white LEFT margin added (the first glyph is the decoder's
        weakest region — the classic "Diovan" -> "ovan" failure), then keep
        whichever reading has better evidence = real_confidence weighted by
        drug-catalog similarity. Bounded: only weak lines, one extra decode.

        Guardrail: a retry candidate that CONTRADICTS Florence's reading of
        the same line is rejected — the retry may only improve agreement with
        the second model, never silently overturn it (a raw confidence bump
        alone once flipped a correct "Crestor 10mg" into "Lansor 100mg").
        """
        florence_texts = florence_texts or []
        if not ocr_settings.retry_enabled or not self.drugs_db:
            return decoded
        catalog_names = [d.get("name", "") for d in self.drugs_db if d.get("name")]
        weak = [i for i, r in enumerate(decoded)
                if r["confidence"] < ocr_settings.retry_conf_threshold and r["text"]]
        if not weak:
            return decoded
        retry_imgs = []
        for i in weak:
            img = crops_images[i]
            if isinstance(img, np.ndarray):
                img = Image.fromarray(img)
            retry_imgs.append(pad_left_white(img.convert("RGB"), ocr_settings.retry_left_pad_ratio))
        retry_decoded = self.read_line_crops_batch(retry_imgs)

        def evidence(r):
            return r["confidence"] * (0.5 + 0.5 * _catalog_score(r["text"], catalog_names))

        out = list(decoded)
        changed = 0
        for pos, i in enumerate(weak):
            alt = retry_decoded[pos]
            if not alt["text"]:
                continue
            f_ref = florence_texts[i] if i < len(florence_texts) else ""
            if f_ref:
                base_agree = agreement_ratio(decoded[i]["text"], f_ref)
                alt_agree = agreement_ratio(alt["text"], f_ref)
                if alt_agree <= base_agree:
                    print(f"[OCR Engine] Left-margin retry REJECTED for line {i + 1}: "
                          f"{alt['text']!r} agrees {alt_agree:.2f} with Florence {f_ref!r} "
                          f"(current reading agrees {base_agree:.2f})")
                    continue
            base_ev = decoded[i]["confidence"] * (0.5 + 0.5 * _catalog_score(decoded[i]["text"], catalog_names))
            alt_ev = alt["confidence"] * (0.5 + 0.5 * _catalog_score(alt["text"], catalog_names))
            # Switch only on a clear win, never on noise-level differences.
            if alt_ev > base_ev * 1.05:
                out[i] = alt
                print(f"[OCR Engine] Left-margin retry upgraded line {i + 1}: "
                      f"{decoded[i]['text']!r} -> {alt['text']!r} (conf {decoded[i]['confidence']:.3f} -> {alt['confidence']:.3f})")
                changed += 1
        print(f"[OCR Engine] Left-margin retry: {len(weak)} weak line(s), {changed} upgraded.")
        return out

    def _florence_box_retry(self, decoded, florence_box_imgs, florence_texts):
        """
        Third hypothesis for still-weak lines: decode the FLORENCE line-box
        crop (the line bbox on the original-resolution image) with TrOCR and
        arbitrate by evidence. The isolation test measured 0.95-0.98 real
        confidence on clean pages where the OpenCV-band crop read wrong —
        this crop provenance matches the fine-tuning crops best.
        Same guardrail as the left-margin retry: a candidate that agrees with
        Florence's reading WORSE than the current one is rejected.
        """
        if not ocr_settings.florence_box_retry_enabled or not self.drugs_db:
            return decoded
        catalog_names = [d.get("name", "") for d in self.drugs_db if d.get("name")]

        def evidence(r):
            return r["confidence"] * (0.5 + 0.5 * _catalog_score(r["text"], catalog_names))

        idx = [i for i, r in enumerate(decoded)
               if r["confidence"] < ocr_settings.retry_conf_threshold
               and r["text"] and florence_box_imgs[i] is not None]
        if not idx:
            return decoded
        imgs = [florence_box_imgs[i] for i in idx]
        box_decoded = self.read_line_crops_batch(imgs)

        out = list(decoded)
        changed = 0
        for pos, i in enumerate(idx):
            alt = box_decoded[pos]
            if not alt["text"]:
                continue
            f_ref = florence_texts[i] if i < len(florence_texts) else ""
            if f_ref:
                base_agree = agreement_ratio(decoded[i]["text"], f_ref)
                alt_agree = agreement_ratio(alt["text"], f_ref)
                if alt_agree <= base_agree:
                    continue
            if evidence(alt) > evidence(decoded[i]) * 1.05:
                out[i] = alt
                print(f"[OCR Engine] Florence-box retry upgraded line {i + 1}: "
                      f"{decoded[i]['text']!r} -> {alt['text']!r} (conf {decoded[i]['confidence']:.3f} -> {alt['confidence']:.3f})")
                changed += 1
        print(f"[OCR Engine] Florence-box retry: {len(idx)} weak line(s), {changed} upgraded.")
        return out

    def _florence_line_verify(self, crops_images, decoded, florence_texts, florence_confs):
        """
        Honest per-line Florence second opinion for weak TrOCR lines.

        The page pass gives every line the SAME page-level confidence (~0.3,
        diluted across box-coordinate tokens), so Florence can lose the fusion
        even when it read the line better. For the weakest lines we re-run
        <OCR_WITH_REGION> on the crop itself (letterboxed — never squashed)
        and replace the page-level evidence with the line-level reading.
        """
        if not ocr_settings.florence_retry_enabled:
            return
        weak = [i for i, r in enumerate(decoded)
                if r["confidence"] < ocr_settings.retry_conf_threshold and r["text"]]
        if not weak:
            return
        weak = weak[: max(1, ocr_settings.florence_retry_max)]
        self.load_florence()
        for i in weak:
            img = crops_images[i]
            if isinstance(img, np.ndarray):
                img = Image.fromarray(img)
            lb = letterbox_square(img.convert("RGB"), ocr_settings.florence_canvas)
            inputs = self.florence_processor(
                text="<OCR_WITH_REGION>", images=lb.image, return_tensors="pt"
            ).to(self.florence_device)
            with torch.inference_mode():
                out = self.florence_model.generate(
                    input_ids=inputs["input_ids"],
                    pixel_values=inputs["pixel_values"],
                    max_new_tokens=ocr_settings.florence_max_new_tokens,
                    num_beams=ocr_settings.florence_num_beams,
                    do_sample=False,
                    use_cache=True,
                    return_dict_in_generate=True,
                    output_scores=True,
                )
            raw_text = self.florence_processor.batch_decode(out.sequences, skip_special_tokens=False)[0]
            parsed = self.florence_processor.post_process_generation(
                raw_text, task="<OCR_WITH_REGION>",
                image_size=(ocr_settings.florence_canvas, ocr_settings.florence_canvas),
            )
            labels = [str(x).replace("</s>", "").strip()
                      for x in parsed.get("<OCR_WITH_REGION>", {}).get("labels", [])]
            line_text = " ".join(l for l in labels if l).strip()
            if not line_text:
                continue
            conf = 0.0
            seq_scores = getattr(out, "sequences_scores", None)
            if seq_scores is not None:
                pad_id = getattr(self.florence_processor.tokenizer, "pad_token_id", None)
                n_tok = int((out.sequences[0] != pad_id).sum().item()) if pad_id is not None else int(out.sequences.shape[1])
                conf = geo_mean_confidence(float(seq_scores[0].item()), n_tok)
            old_t, old_c = florence_texts[i], florence_confs[i]
            florence_texts[i] = line_text
            florence_confs[i] = conf
            print(f"[OCR Engine] Florence line re-read L{i + 1}: {line_text!r} conf={conf:.3f} "
                  f"(was {old_t!r} conf={old_c:.3f})")

    def process_prescription(self, image_input, use_florence=True, raw_bytes=None):
        """
        Hybrid Vision-Language Prescription Pipeline (v4.1):
        0. Orientation (EXIF) → deskew → light photometric enhancement (CPU).
        1. Florence-2 detects headers/metadata and generates the image fingerprint
           (aspect-preserving letterboxed page, real page confidence).
        2. OpenCV classical segmentation isolates text lines (on the deskewed image).
        3. OpenCV crops overlapping Florence header boxes are dropped.
        4. TrOCR decodes each ink-bounded crop (letterboxed, upscaled if tiny) and
           reports real decoder confidence.
        5. Fusion weighs both hypotheses by evidence; disagreements are capped and
           flagged so the backend traffic light forces a pharmacist review.
        """
        excluded_header_lines = []; excluded_header_bboxes = []
        rejected_phantom_candidates = []
        florence_error = None
        image_fingerprint = None
        header_bboxes = []
        florence_crops = []
        deskew_angle = 0.0
        
        if isinstance(image_input, list):
            crops_data = image_input
            detection_engine = "custom_crops"
        else:
            detection_engine = "opencv_projection"

            # ── Geometric + photometric preprocessing BEFORE segmentation ──
            # Pipeline order (2026-09 review): orientation → deskew → light
            # enhancement → segmentation → line crops → TrOCR/Florence.
            # A tilted page corrupts the horizontal projection profile, and a
            # shadowed photo hurts both recognizers. Enhancement keeps the
            # image natural (color, no binarization) for the models.
            if isinstance(image_input, str):
                with open(image_input, "rb") as rf:
                    path_bytes = rf.read()
                if raw_bytes is None:
                    raw_bytes = path_bytes
                work_pil = Image.open(io.BytesIO(path_bytes)).convert("RGB")
            elif isinstance(image_input, np.ndarray):
                work_pil = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB))
            elif isinstance(image_input, Image.Image):
                work_pil = image_input.convert("RGB")
            else:
                raise ValueError("Unsupported image input format.")

            work_pil = apply_exif_orientation(work_pil)
            if ocr_settings.deskew_enabled:
                work_pil, deskew_angle = deskew_pil(
                    work_pil,
                    max_deg=ocr_settings.deskew_max_deg,
                    min_deg=ocr_settings.deskew_min_deg,
                )
                if deskew_angle:
                    print(f"[OCR Engine] Deskewed page by {deskew_angle} degrees.")
            if ocr_settings.enhance_enabled:
                work_pil = enhance_for_recognition(
                    work_pil,
                    flatten=ocr_settings.illumination_flatten,
                    clahe=ocr_settings.clahe_enabled,
                    denoise=ocr_settings.denoise_enabled,
                    clahe_clip=ocr_settings.clahe_clip,
                )
            image_input = work_pil

            if use_florence:
                try:
                    # Florence provides: headers + fingerprint, AND per-line
                    # readings (it is the printed-text expert — TrOCR drops
                    # leading glyphs on clean printed lines). Its line boxes
                    # are fused per-line below by vertical overlap.
                    florence_crops, excl_headers, fingerprint, excl_bboxes = self.segment_lines_florence(image_input, raw_bytes=raw_bytes)
                    image_fingerprint = fingerprint
                    excluded_header_lines = excl_headers
                    header_bboxes = excl_bboxes
                    print(f"[OCR Engine] Florence-2 extracted fingerprint, {len(excluded_header_lines)} headers "
                          f"and {len(florence_crops)} line reading(s).")
                except Exception as e:
                    import traceback
                    florence_error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
                    print(f"[OCR Engine] Florence-2 metadata extraction failed: {florence_error}")
                    florence_crops = []

            # Primary: OpenCV classical segmentation (best for fine-tuned TrOCR crops)
            raw_opencv_crops = self.segment_lines(image_input)

            # Filter out OpenCV crops that fall inside Florence's header bboxes
            filtered_crops = []
            for crop in raw_opencv_crops:
                cx = (crop["bbox"][1] + crop["bbox"][3]) / 2
                cy = (crop["bbox"][0] + crop["bbox"][2]) / 2

                is_header = False
                for h_box in header_bboxes:
                    hx1, hy1, hx2, hy2 = h_box
                    # Give it a small margin
                    if (hx1 - 20) <= cx <= (hx2 + 20) and (hy1 - 15) <= cy <= (hy2 + 15):
                        is_header = True
                        break

                if not is_header:
                    filtered_crops.append(crop)
                else:
                    print(f"[OCR Engine] Dropped OpenCV crop at y={cy} (overlapped with Florence header)")

            crops_data = filtered_crops

            # Fuse Florence's own line readings into the OpenCV crops: the
            # line whose box overlaps the OpenCV band vertically (>40% of the
            # smaller band) donates its text + confidence to the fusion stage.
            for crop in crops_data:
                cy1, cx1, cy2, cx2 = crop["bbox"]
                best, best_ov = None, 0.0
                for fb in florence_crops:
                    fy1, fx1, fy2, fx2 = fb["bbox"]
                    ov = min(cy2, fy2) - max(cy1, fy1)
                    if ov > best_ov:
                        best_ov, best = ov, fb
                min_h = min(cy2 - cy1, (best["bbox"][2] - best["bbox"][1])) if best else 0
                if best is not None and best.get("florence_text") and best_ov > 0.4 * max(1, min_h):
                    crop["florence_text"] = best["florence_text"]
                    crop["florence_conf"] = best.get("florence_conf", 0.0)
                    # Keep the Florence-box crop itself: feeding this line bbox
                    # (original resolution) directly to TrOCR is the proven
                    # third hypothesis for weak lines.
                    crop["florence_box_image"] = best.get("image")

            print(f"[OCR Engine] OpenCV segmented {len(raw_opencv_crops)} lines, kept {len(crops_data)} after header filtering.")


        if not crops_data:
            return {
                "total_lines_detected": 0,
                "medications_found": 0,
                "medications": [],
                "excluded_header_lines": excluded_header_lines,
                "rejected_phantom_candidates": [],
                "pipeline": "hybrid_florence_trocr",
                "prompt_version": "v4.0-strict"
            }

        crops_images = []
        crops_bboxes = []
        florence_texts = []
        florence_confs = []
        florence_box_imgs = []
        for crop_info in crops_data:
            if isinstance(crop_info, dict):
                crops_images.append(crop_info["image"])
                crops_bboxes.append(crop_info.get("bbox"))
                florence_texts.append(crop_info.get("florence_text", ""))
                florence_confs.append(float(crop_info.get("florence_conf", 0.0) or 0.0))
                florence_box_imgs.append(crop_info.get("florence_box_image"))
            else:
                crops_images.append(crop_info)
                crops_bboxes.append(None)
                florence_texts.append("")
                florence_confs.append(0.0)
                florence_box_imgs.append(None)

        # Checkpoint 3: TrOCR Inference
        fp_sha256 = image_fingerprint.get("sha256", "unknown") if image_fingerprint else "unknown"
        print(f"\n[PIPELINE AUDIT - Checkpoint 3: TrOCR Inference] Source Image SHA256: {fp_sha256} | Decoding {len(crops_images)} line crops simultaneously on {self.trocr_device.upper()}")

        # Batch Inference: decode all segmented line crops in bounded
        # micro-batches; each result carries its REAL decoder confidence.
        decoded = self.read_line_crops_batch(crops_images)
        # Second opinion for weak lines (dropped-first-glyph recovery);
        # Florence's own readings guard the retry against contradictions.
        decoded = self._retry_weak_lines(crops_images, decoded, florence_texts)
        # Third hypothesis: TrOCR on the Florence line-box crop for lines still
        # weak (this crop provenance matches the fine-tuning distribution best).
        decoded = self._florence_box_retry(decoded, florence_box_imgs, florence_texts)
        # Honest per-line Florence confidence for lines still weak after the
        # left-margin retry (fixes the page-level confidence dilution).
        try:
            self._florence_line_verify(crops_images, decoded, florence_texts, florence_confs)
        except Exception as e:
            print(f"[OCR Engine] Florence line verification skipped: {type(e).__name__}: {e}")
        trocr_texts = [d["text"] for d in decoded]
        trocr_confs = [d["confidence"] for d in decoded]

        results = []
        line_num = 1
        for idx, (trocr_text, f_text, bbox, c_img) in enumerate(zip(trocr_texts, florence_texts, crops_bboxes, crops_images)):
            florence_conf = florence_confs[idx] if idx < len(florence_confs) else 0.0
            # Skip obvious header/footer/diagnosis noise
            if re.match(r'^(rx|patient|age|date|d[x\:\.]|diag|diagnosis|signed):?', trocr_text, re.IGNORECASE) or \
               any(cond in trocr_text.lower() for cond in ["rhinitis", "pharyngitis", "seasonallah", "hypertension", "gastritis"]):
                excluded_header_lines.append(f"{trocr_text} (Diagnosis/Header noise)")
                continue

            # Strip leading numbers (e.g. "1.", "2-", "3)", "1:") from text so line_number is the sole source of truth
            clean_trocr = re.sub(r'^\s*\d+[\.\-\)\:]\s*', '', trocr_text).strip()
            clean_florence = re.sub(r'^\s*\d+[\.\-\)\:]\s*', '', f_text).strip()

            chosen_text, v_style, conf, is_disagreement = self.fuse_ocr_hypotheses(
                clean_trocr, clean_florence,
                trocr_conf=trocr_confs[idx] if idx < len(trocr_confs) else 0.0,
                florence_conf=florence_conf,
            )
            chosen_raw = chosen_text if chosen_text else (clean_trocr if clean_trocr else clean_florence)

            chosen_raw = re.sub(r'(\s*-\s*\d+\s*(?:tab|tabs|cap|caps))+\s*$', '', chosen_raw, flags=re.IGNORECASE)

            # NOTE (safety, 2026-09 review): the old "post-OCR drug name
            # correction" that overwrote the first word with the nearest
            # catalog entry was REMOVED. It could silently INVENT a drug name
            # from a hallucinated token (the exact failure mode it claimed to
            # fix). Catalog resolution stays exclusively in the backend
            # matching layer, which enforces LASA/strength guards and never
            # mutates raw OCR text.
            
            # Isolate drug name by removing strength and instructions to check validity
            name_part = chosen_raw
            if '-' in name_part:
                name_part = name_part.split('-')[0].strip()
            name_part = re.sub(r'(\d+(?:\.\d+)?(?:\/\d+(?:\.\d+)?)?\s*(?:mg|g|mcg|ml|iu|%))', '', name_part, flags=re.I)
            name_part = re.sub(r'\b(tabs?|caps?|sachets?|drops?|gel|cream|vials?|ampoules?|syrups?)\b', '', name_part, flags=re.I)
            name_part = re.sub(r'[^a-zA-Z]', '', name_part).strip().lower()

            # Reject standalone words or phantom fragments (v4.0-strict Rule 2)
            if name_part in ["stop", "iu", "none", "bottle", "null", "tab", "tabs", "caps", "vial"] or len(name_part) < 3:
                rejected_phantom_candidates.append(f"{chosen_raw} (Phantom artifact / Non-medication structure)")
                continue

            # Fragment Rejection (v4.0-strict Rule 3):
            alpha_chars = re.findall(r'[a-zA-Z]', chosen_raw)
            alpha_count = len(alpha_chars)
            standalone_units = {"stop", "iu", "i.u", "mg", "ml", "tab", "tabs", "caps", "cap", "gm", "mcg", "g"}
            is_standalone_unit = chosen_raw.lower().strip() in standalone_units

            is_fragment = (alpha_count < 4) or is_standalone_unit
            is_illeg = is_fragment or (len(clean_trocr) < 3 and len(clean_florence) < 3)

            # v5.0-strict: Separation of Confidences & Visual Legibility Guard
            # Pure visual check before any catalog matching:
            raw_trocr_c = float(trocr_confs[idx] if idx < len(trocr_confs) else 0.0)
            has_repeating_gibberish = bool(re.search(r'(.)\1{3,}', clean_trocr))
            has_illegible_noise = bool(re.search(r'[\?\.]{3,}', clean_trocr)) or has_repeating_gibberish

            danger_sign_detected = (
                raw_trocr_c < 0.40 or
                has_illegible_noise or
                (alpha_count < 4 and not is_standalone_unit)
            )

            if danger_sign_detected:
                is_illeg = True
                conf = min(conf, 0.25)
                legibility_reasoning = "تراكب شديد في الحروف أو خط غير مقروء بصرياً بدون حدود واضحة للكلمة"
            elif is_fragment:
                is_illeg = True
                conf = min(conf, 0.28)
                legibility_reasoning = "شظية نصية قصيرة أقل من 4 حروف متتالية بدون سياق دوائي كامل"
            elif is_disagreement:
                conf = min(conf, 0.70)
                legibility_reasoning = "اختلاف في القراءة البصرية بين النموذجين، بحاجة لمراجعة الصيدلي"
            elif conf >= 0.85:
                legibility_reasoning = "حروف متمايزة وواضحة بصرياً مع خط أساس منتظم وخلو من التراكب"
            else:
                legibility_reasoning = "قراءة بصرية متوسطة الوضوح، يُفضل مراجعة الصيدلي للتأكيد"

            cropped_image_b64 = None
            if c_img is not None:
                try:
                    buf = io.BytesIO()
                    if isinstance(c_img, np.ndarray):
                        c_pil = Image.fromarray(c_img)
                    else:
                        c_pil = c_img
                    c_pil.save(buf, format="JPEG")
                    cropped_image_b64 = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
                except Exception:
                    pass

            # Combine strengths: TrOCR has medical format structure, Florence has exact raw characters
            results.append({
                "line_number": line_num,
                "raw_name": chosen_raw,
                "trocr_text": clean_trocr,
                "florence_text": clean_florence,
                "ocr_confidence": conf,
                "trocr_confidence": round(float(trocr_confs[idx] if idx < len(trocr_confs) else 0.0), 4),
                "florence_confidence": round(float(florence_conf), 4),
                "is_illegible": is_illeg,
                "is_fragment_too_short": is_fragment,
                "visual_style": v_style,
                "model_disagreement": is_disagreement,
                "visual_evidence_ok": True,
                "legibility_reasoning": legibility_reasoning,
                "bbox": bbox,
                "cropped_image": cropped_image_b64,
                "engine": detection_engine
            })
            line_num += 1

        # Deduplication safety net: an over-eager band split can read the SAME
        # line from overlapping sliver crops (3 drugs -> 9 duplicated items).
        # Merge readings that agree in text AND overlap in position; keep the
        # highest-confidence one.
        deduped = []
        for m in sorted(results, key=lambda x: -float(x.get('ocr_confidence') or 0)):
            dup = False
            for k in deduped:
                mb, kb = m.get('bbox'), k.get('bbox')
                if not (mb and kb):
                    continue
                ov = min(mb[2], kb[2]) - max(mb[0], kb[0])
                if ov > 0.5 * max(1, min(mb[2] - mb[0], kb[2] - kb[0])) and                    agreement_ratio(m.get('raw_name', ''), k.get('raw_name', '')) >= 0.80:
                    dup = True
                    break
            if not dup:
                deduped.append(m)
        if len(deduped) != len(results):
            print(f"[OCR Engine] Deduplicated {len(results) - len(deduped)} duplicate line(s).")
        results = sorted(deduped, key=lambda x: (x.get('bbox') or [9999])[0])
        for i, m in enumerate(results, start=1):
            m['line_number'] = i

        # Cross-line Repetition / Mode Collapse Guard:
        # Detect if TrOCR repeated the same drug name across distinct non-overlapping lines
        # on the same prescription page (a known generative decoder failure mode).
        name_counts = {}
        for m in results:
            clean_n = re.sub(r'[^a-zA-Z0-9]', '', (m.get('raw_name') or '').lower())
            if len(clean_n) >= 4:
                name_counts[clean_n] = name_counts.get(clean_n, 0) + 1

        for m in results:
            clean_n = re.sub(r'[^a-zA-Z0-9]', '', (m.get('raw_name') or '').lower())
            if len(clean_n) >= 4 and name_counts.get(clean_n, 0) > 1:
                m['model_disagreement'] = True
                m['is_illegible'] = True
                m['ocr_confidence'] = min(float(m.get('ocr_confidence') or 0.0), 0.35)
                m['legibility_reasoning'] = "اشتباه في تكرار آلي لنفس الدواء في سطرين منفصلين، بحاجة لمراجعة الصيدلي"

        # Release the PyTorch caching-allocator blocks back to the driver: on a
        # shared 4GB card (Ollama/other tenants) this avoids fragmentation OOM.
        if self.trocr_device == "cuda":
            torch.cuda.empty_cache()

        return {
            "image_fingerprint": image_fingerprint or {
                "sha256": "unknown",
                "top_left_visible_text": "N/A",
                "clinic_name_guess": "Unknown",
                "patient_name_guess": "Unknown",
                "approximate_image_orientation": "portrait",
                "number_of_handwritten_lines_visible": len(results)
            },
            "total_lines_detected": len(crops_data),
            "medications_found": len(results),
            "medications": results,
            "excluded_header_lines": excluded_header_lines,
            "rejected_phantom_candidates": rejected_phantom_candidates,
            "florence_error": florence_error,
            "pipeline": "hybrid_florence_trocr",
            "prompt_version": "v5.0-strict",
            "preprocessing": {
                "deskew_angle": deskew_angle,
                "trocr_letterbox": bool(ocr_settings.trocr_letterbox),
                "florence_canvas": ocr_settings.florence_canvas,
            }
        }

if __name__ == "__main__":
    print("[OCR Engine] Running in vision-only mode. Fuzzy matching delegated to backend.")






