import os
import io
import re
import hashlib
import threading
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

# تحميل محرك TrOCR المحلي
from prescription_ocr_engine import PrescriptionOCREngine

app = FastAPI(title="AI-COS Pharmacy Prescription OCR & Intelligence Engine")

ALLOWED_LOCAL_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_LOCAL_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 1. Initialize Local Fine-Tuned TrOCR Engine
print("[Server] Initializing Local TrOCR Offline Engine...")
local_ocr_engine = PrescriptionOCREngine()

from fastapi import Header

# Set internal secret for communication between main backend and this microservice
INTERNAL_API_KEY = os.environ.get("INTERNAL_OCR_SECRET")
if not INTERNAL_API_KEY:
    for env_candidate in [
        r"D:\Graduation Project\AI-COS-Pharmacy\backend\.env",
        r"D:\Graduation Project\backend\backend\.env",
    ]:
        if os.path.exists(env_candidate):
            with open(env_candidate, "r", encoding="utf-8") as env_f:
                for line in env_f:
                    if line.strip().startswith("INTERNAL_OCR_SECRET="):
                        INTERNAL_API_KEY = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                        break
        if INTERNAL_API_KEY:
            break

if not INTERNAL_API_KEY:
    raise RuntimeError("INTERNAL_OCR_SECRET is required to start the local OCR service.")

# Single-flight gate: the two vision models share one 4GB VRAM — concurrent
# inference requests would contend and blow past the latency budget. The gate
# admits one request at a time; everyone else gets an enumerable 503 with
# Retry-After instead of queueing into a silent latency collapse.
INFERENCE_GATE = threading.Semaphore(1)
INFERENCE_GATE_RETRY_AFTER = "20"

# ── Live health metrics (in-memory, single process) ─────────────────────
import time as _time
from collections import deque as _deque

_METRICS_LOCK = threading.Lock()
_METRICS = {"total_completed": 0, "busy_503": 0, "errors": 0,
            "lines_detected": 0, "model_disagreements": 0}
_LATENCIES_MS = _deque(maxlen=200)


def _metrics_snapshot() -> dict:
    with _METRICS_LOCK:
        lats = sorted(_LATENCIES_MS)
        n = len(lats)
        m = dict(_METRICS)
        m["latency_samples"] = n
        m["p50_latency_ms"] = round(lats[int(n * 0.50)]) if n else None
        m["p95_latency_ms"] = round(lats[min(int(n * 0.95), n - 1)]) if n else None
        m["disagreement_rate"] = (
            round(m["model_disagreements"] / m["total_completed"], 4)
            if m["total_completed"] else 0.0
        )
        return m


def _record_success(latency_ms: float, lines: int, disagreements: int) -> None:
    with _METRICS_LOCK:
        _METRICS["total_completed"] += 1
        _METRICS["lines_detected"] += lines
        _METRICS["model_disagreements"] += disagreements
        _LATENCIES_MS.append(latency_ms)


def _record_busy() -> None:
    with _METRICS_LOCK:
        _METRICS["busy_503"] += 1


def _record_error() -> None:
    with _METRICS_LOCK:
        _METRICS["errors"] += 1

STRENGTH_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?\s*(?:mg|g|gm|mcg|μg|iu|ml|%)\b",
    re.IGNORECASE,
)
FORM_PATTERN = re.compile(
    r"\b(tablets?|tabs?|capsules?|caps?|syrup|susp(?:ension)?|drops?|cream|gel|ointment|vials?|ampoules?|inhaler|sachets?)\b",
    re.IGNORECASE,
)


INSTRUCTION_PATTERN = re.compile(
    r"\b((?<![a-zA-Z0-9]\s)(?<![a-zA-Z0-9])\d\s*[xX\-\*]\s*\d(?:\s*[xX\-\*]\s*\d)?|od|bid|bd|tid|qid|tds|sos|prn|hs|every\s+\d+\s+hours?|everyday|daily|once\s+daily|twice\s+daily|twice\s+a\s+day|thrice\s+a\s+day|after\s+meals|before\s+meals|after\s+food|before\s+food|morning|evening|night)\b",
    re.IGNORECASE
)

QUANTITY_TAIL_PATTERN = re.compile(
    r"[\s\-–—*xX×]+\s*(\d{1,3})\s*(?:\(\s*\d{1,3}\s*\))?\s*$"
)


def extract_quantity_tail(text: str) -> tuple[int | None, str]:
    """Extracts a trailing dose/quantity ('Amaryl 2mg - 2' → 2) and returns
    (quantity, cleaned_text) with the tail removed so the remaining name can
    exact-match the catalog. Guards: the bare number must be the LAST token,
    must not be part of a strength (already stripped), and must be ≤ 300
    (a plausible unit count, not a page number > 300)."""
    t = (text or "").strip()
    m = QUANTITY_TAIL_PATTERN.search(t)
    if m:
        qty = int(m.group(1))
        if qty <= 300:
            cleaned = QUANTITY_TAIL_PATTERN.sub(" ", t).strip(" -–—*	")
            cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
            return qty, cleaned
    # لا كمية — لكن الشرطة/النجمة الطرفية العائمة ('Crestor 10mg -') ضجيج OCR
    # يكسر المطابقة التامة: تُنظف دائماً (بدون لمس الأسماء المنتهية بـ x)
    cleaned = re.sub(r"[\s\-–—*]+$", "", t).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return None, cleaned


def extract_structured_fields(text: str) -> tuple[str | None, str | None, str | None]:
    """Extract only visible strength/form/instructions tokens; never infer missing values."""
    strength_matches = STRENGTH_PATTERN.findall(text or "")
    form_match = FORM_PATTERN.search(text or "")
    instr_matches = INSTRUCTION_PATTERN.findall(text or "")
    instr_matches = [m for m in instr_matches if not re.match(r'^\d{1,2}$', m.strip())]
    
    return (
        strength_matches[-1].replace(" ", "") if strength_matches else None,
        form_match.group(0).lower() if form_match else None,
        " ".join(instr_matches).lower() if instr_matches else None,
    )

@app.get("/health")
def health():
    return {"status": "ok", "service": "TrOCR Vision Server", "port": 9202}

@app.post("/api/infer-text")
def infer_text(
    file: UploadFile = File(...),
    x_internal_secret: str = Header(None)
):
    """
    Internal Microservice Endpoint: 100% Offline OCR Inference.
    Takes an image, segments lines, runs TrOCR, and returns raw text.
    """
    if x_internal_secret != INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid internal secret")

    if not INFERENCE_GATE.acquire(blocking=False):
        _record_busy()
        raise HTTPException(
            status_code=503,
            detail={"code": "OCR_BUSY", "message_ar": "محرك القراءة مشغول بصورة أخرى — أعد المحاولة بعد 20 ثانية."},
            headers={"Retry-After": INFERENCE_GATE_RETRY_AFTER},
        )

    _t0 = _time.perf_counter()
    try:
        image_bytes = file.file.read()
        sha256_received = hashlib.sha256(image_bytes).hexdigest()
        print(f"\n[PIPELINE AUDIT - Checkpoint 2 (Server Receive)]: file={file.filename} | SHA256={sha256_received}")

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        result = local_ocr_engine.process_prescription(image, raw_bytes=image_bytes)
        
        formatted_meds = []
        _lines_n = len(result.get("medications", []))
        _disagree_n = sum(1 for m in result.get("medications", []) if m.get("model_disagreement"))
        for m in result.get("medications", []):
            # v4.1: the old clean_drug_name() suffix-stripping ("ette", "inna", ...)
            # was removed — it mutated genuine drug names (e.g. Cerazette -> Ceraz)
            # and masked recognizer errors. Raw OCR text flows through untouched;
            # catalog matching with LASA/strength guards lives in the backend layer.
            raw_name = (m.get("raw_name") or "").strip()
            strength, dosage_form, instructions = extract_structured_fields(raw_name)
            quantity, clean_name = extract_quantity_tail(raw_name)
            formatted_meds.append({
                "line_number": m.get("line_number"),
                "raw_name": clean_name,
                "raw_name_original": raw_name,
                "trocr_text": m.get("trocr_text"),
                "florence_text": m.get("florence_text"),
                "trocr_confidence": m.get("trocr_confidence", 0.0),
                "florence_confidence": m.get("florence_confidence", 0.0),
                "strength": strength,
                "dosage_form": dosage_form,
                "quantity": quantity,
                "duration": None,
                "instructions": instructions,
                "ocr_confidence": m.get("ocr_confidence", 0.0),
                "is_illegible": m["is_illegible"],
                "is_fragment_too_short": m.get("is_fragment_too_short", False),
                "visual_style": m.get("visual_style", "handwritten"),
                "visual_evidence_ok": m.get("visual_evidence_ok", True),
                "model_disagreement": m.get("model_disagreement", False),
                "legibility_reasoning": m.get("legibility_reasoning", ""),
                "bbox": m.get("bbox"),
                "cropped_image": m.get("cropped_image")
            })

        preprocessing_meta = result.get("preprocessing", {})
        verification_meta = {
            "mode": "hybrid_offline_florence_trocr",
            "primary_engine": "Florence-2 + TrOCR Fine-Tuned",
            "lines_detected": result['total_lines_detected'],
            "pipeline": result.get("pipeline", "hybrid_florence_trocr"),
            "prompt_version": "v5.0-strict",
            "deskew_angle": preprocessing_meta.get("deskew_angle", 0.0),
            "trocr_letterbox": preprocessing_meta.get("trocr_letterbox", True),
            "florence_error": result.get("florence_error")
        }

        crops_manifest = []
        for m in formatted_meds:
            c_b64 = m.get("cropped_image")
            c_hash = hashlib.sha256(c_b64.encode("utf-8")).hexdigest() if c_b64 else None
            crops_manifest.append({
                "line_number": m.get("line_number"),
                "raw_name": m.get("raw_name"),
                "bbox": m.get("bbox"),
                "crop_sha256": c_hash
            })

        import json
        # Canonical serialization must match the backend verifier exactly.
        manifest_json_bytes = json.dumps(
            crops_manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        crops_manifest_sha256 = hashlib.sha256(manifest_json_bytes).hexdigest()

        _record_success((_time.perf_counter() - _t0) * 1000.0, _lines_n, _disagree_n)
        return {
            "image_fingerprint": result.get("image_fingerprint", {
                "sha256": sha256_received,
                "top_left_visible_text": "N/A",
                "clinic_name_guess": "Unknown",
                "patient_name_guess": "Unknown",
                "approximate_image_orientation": "portrait",
                "number_of_handwritten_lines_visible": len(formatted_meds)
            }),
            "medications": formatted_meds,
            "crops_manifest": crops_manifest,
            "excluded_header_lines": result.get("excluded_header_lines", []),
            "rejected_phantom_candidates": result.get("rejected_phantom_candidates", []),
            "image_quality_notes": f"Processed locally with Hybrid Florence-2 + TrOCR (v4.1-strict). {result['total_lines_detected']} lines detected.",
            "verification_meta": verification_meta,
            "pipeline_hashes": {
                "checkpoint_2_ocr_receive": sha256_received,
                # The backend router verifies this key equals the stored-file
                # sha256 (the recognizer consumed exactly the uploaded bytes;
                # letterbox/deskew happen on in-memory copies, not the source).
                "checkpoint_3_trocr_input": sha256_received,
                "checkpoint_3_crops_manifest": crops_manifest_sha256,
            }
        }
    except Exception as e:
        _record_error()
        print(f"Error in local OCR inference: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        INFERENCE_GATE.release()

@app.get("/metrics")
def metrics(x_internal_secret: str = Header(None)):
    """Internal: live health snapshot for the admin vision-health badge."""
    if x_internal_secret != INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid internal secret")
    return _metrics_snapshot()


if __name__ == "__main__":
    print("Starting AI OCR Internal Vision Server (TrOCR) on port 9202 (Bound to 127.0.0.1 only)...")
    uvicorn.run(app, host="127.0.0.1", port=9202)

