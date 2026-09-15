# -*- coding: utf-8 -*-
"""
Central configuration for the local OCR engine (TrOCR + Florence-2 only).

Every knob is overridable with an environment variable (see start_ocr.bat),
so the pipeline can be tuned for the deployment GPU (NVIDIA T1200, 4GB VRAM)
without code changes. Defaults are conservative: they fit VRAM, keep CPU work
light, and fix the aspect-ratio / confidence bugs found in the 2026-09 review.
"""
import os


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class OCRSettings:
    # ---- TrOCR recognition -------------------------------------------------
    # Model encoder grid is fixed at 384x384; we letterbox instead of squashing.
    trocr_input_size: int = _env_int("TROCR_INPUT_SIZE", 384)
    # PREPROCESSING MUST MATCH THE DEPLOYED CHECKPOINT'S TRAINING.
    # The current trocr-finetuned-final was trained on SQUASHED 384x384 crops:
    # enabling letterbox at inference without retraining collapses its accuracy
    # (measured: exact 95% -> 2% on its own dataset). Default therefore False;
    # flip TROCR_LETTERBOX=1 ONLY after retraining with the aligned
    # finetune_trocr.py (which reads this same flag for consistency).
    trocr_letterbox: bool = _env_bool("TROCR_LETTERBOX", True)
    # GPU micro-batch for decoding crops (keeps activations bounded on 4GB VRAM).
    trocr_batch_size: int = min(_env_int("TROCR_BATCH_SIZE", 8), 16)
    trocr_num_beams: int = _env_int("TROCR_NUM_BEAMS", 2)
    trocr_repetition_penalty: float = _env_float("TROCR_REPETITION_PENALTY", 1.3)
    trocr_min_content_h: int = _env_int("TROCR_MIN_CONTENT_H", 110)

    # ---- Florence-2 page pass ----------------------------------------------
    # Square canvas the page is letterboxed into (aspect-preserving). Florence-2
    # was trained at 768; keep default 768 on a 4GB card. <= 832 max supported.
    florence_canvas: int = min(_env_int("FLORENCE_CANVAS", 768), 832)
    florence_num_beams: int = _env_int("FLORENCE_NUM_BEAMS", 3)
    florence_max_new_tokens: int = _env_int("FLORENCE_MAX_NEW_TOKENS", 512)
    # Florence device driver: keep "cpu" to reserve VRAM for TrOCR (default), or
    # "cuda" for faster page pass if VRAM headroom exists.
    florence_device: str = os.environ.get("FLORENCE_DEVICE", "cpu").strip().lower()

    # ---- Geometric correction (before segmentation) -------------------------
    deskew_enabled: bool = _env_bool("OCR_DESKEW", True)
    # Rotation beyond this is treated as a mis-detection (never deskew blindly).
    deskew_max_deg: float = _env_float("OCR_DESKEW_MAX_DEG", 12.0)
    # Ignore sub-degree estimates: on already-level pages the estimator's
    # half-degree noise is a false positive, and rotating a level page fills
    # the projection-profile valleys between tightly-spaced lines (they merge).
    deskew_min_deg: float = _env_float("OCR_DESKEW_MIN_DEG", 1.0)

    # ---- Photometric enhancement (CPU, light) --------------------------------
    # Default OFF: the deployed checkpoint was trained on crops WITHOUT
    # illumination flattening/CLAHE, and enhancing before cropping shifts the
    # input away from its training distribution (measured drop). Enable only
    # together with a retrained checkpoint.
    enhance_enabled: bool = _env_bool("OCR_ENHANCE", False)
    # Illumination flatten: divide by a heavily blurred background estimate.
    illumination_flatten: bool = _env_bool("OCR_FLATTEN_ILLUMINATION", True)
    # Mild CLAHE on the L channel only (no harsh binarization for the models).
    clahe_enabled: bool = _env_bool("OCR_CLAHE", True)
    clahe_clip: float = _env_float("OCR_CLAHE_CLIP", 2.0)
    # Colored denoise is the slowest step; keep off by default on CPU.
    denoise_enabled: bool = _env_bool("OCR_DENOISE", False)

    # ---- Line crop construction ----------------------------------------------
    # Padding around the ink bounding box (NOT a fixed page-percentage strip).
    crop_pad_x_ratio: float = _env_float("OCR_CROP_PAD_X", 0.10)
    crop_pad_y_ratio: float = _env_float("OCR_CROP_PAD_Y", 0.18)
    crop_pad_px: int = _env_int("OCR_CROP_PAD_PX", 10)
    # Extra LEFT-biased padding: TrOCR most often drops the FIRST glyph of a
    # line (decoder start is the weakest cross-attention region), so the left
    # margin gets a larger multiplier than the right.
    crop_pad_left_ratio: float = _env_float("OCR_CROP_PAD_LEFT", 0.20)

    # ---- Low-confidence left-margin retry -------------------------------------
    # Lines decoded below this real confidence get a second decode with a
    # white left margin added (gives the first glyph a clear start); the
    # reading with better catalog evidence wins. Bounded: only weak lines.
    retry_enabled: bool = _env_bool("OCR_RETRY_ENABLED", True)
    retry_conf_threshold: float = _env_float("OCR_RETRY_CONF", 0.80)
    retry_left_pad_ratio: float = _env_float("OCR_RETRY_LEFT_PAD", 0.35)

    # ---- Per-line Florence verification (weak lines only) ---------------------
    # The page-level Florence confidence is diluted across box-coordinate
    # tokens (~0.3), so it unfairly loses to TrOCR's real per-line score even
    # when Florence read the line BETTER. For weak lines we re-run Florence on
    # the crop itself (letterboxed) to get an honest per-line confidence.
    # Bounded to the N weakest lines per page to protect latency (CPU).
    florence_retry_enabled: bool = _env_bool("OCR_FLORENCE_RETRY", True)
    florence_retry_max: int = _env_int("OCR_FLORENCE_RETRY_MAX", 3)
    # Third hypothesis: decode the FLORENCE BOX crop (line bbox on the
    # original-resolution image) with TrOCR for weak lines — measured 0.95+
    # confidence on clean pages where the OpenCV-band crop reads wrong.
    florence_box_retry_enabled: bool = _env_bool("OCR_FLORENCE_BOX_RETRY", True)

    # Upscale small crops so handwriting text height reaches the encoder's
    # comfort zone before letterboxing (never upscale upscale more than 3x).
    min_text_height_px: int = _env_int("OCR_MIN_TEXT_HEIGHT", 48)
    max_upscale: float = _env_float("OCR_MAX_UPSCALE", 3.0)


settings = OCRSettings()
