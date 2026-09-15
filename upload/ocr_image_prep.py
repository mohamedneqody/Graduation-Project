# -*- coding: utf-8 -*-
"""
CPU-only image preparation utilities shared by the OCR engine (TrOCR + Florence).

All functions are pure (image in -> image out, no model state) so they can be
unit-tested without loading any model.

Design rules (2026-09 architecture review):
  - Recognition models receive natural, mildly-enhanced COLOR images.
    Binarization is used ONLY for internal segmentation masks / ink bounds,
    never as model input.
  - Aspect ratio is never distorted: `letterbox_square` pads with white
    instead of squashing (fixes the 1500x90 -> 384x384 accuracy killer).
  - Deskew happens BEFORE segmentation so horizontal projection profiles see
    level text bands.
"""
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageOps


# ---------------------------------------------------------------------------
# Orientation / deskew
# ---------------------------------------------------------------------------

def apply_exif_orientation(pil_img: Image.Image) -> Image.Image:
    """Honor the phone camera EXIF orientation tag (cheap orientation fix)."""
    try:
        return ImageOps.exif_transpose(pil_img)
    except Exception:
        return pil_img


def estimate_skew_tilt(bgr: np.ndarray, max_deg: float = 12.0, step: float = 0.5) -> float:
    """
    Estimate the text tilt angle by maximizing the sharpness of the horizontal
    projection profile over candidate rotations. Version-proof (no reliance on
    cv2.minAreaRect angle conventions) and fast: runs on a downscaled copy.

    Returns the tilt in degrees in [-max_deg, max_deg]: the counter-clockwise
    rotation that levels the text lines (0 when already level).
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    scale = min(1.0, 700.0 / max(h, w))
    if scale < 1.0:
        gray = cv2.resize(gray, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA)

    # Ink mask (inverted): adaptive threshold handles phone-photo illumination.
    ink = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    # Keep only the central columns: rotation corner artifacts, margin stamps
    # and side notes otherwise dominate the row profile.
    ih, iw = ink.shape
    ink = ink[:, int(iw * 0.15):int(iw * 0.85)]
    ih, iw = ink.shape
    center = (iw / 2.0, ih / 2.0)

    best_angle, best_score = 0.0, -1.0
    angles = np.arange(-max_deg, max_deg + 1e-6, step)
    for ang in angles:
        m = cv2.getRotationMatrix2D(center, ang, 1.0)
        rotated = cv2.warpAffine(ink, m, (iw, ih), flags=cv2.INTER_NEAREST, borderValue=0)
        profile = rotated.astype(np.float32).sum(axis=1)
        # Smooth before scoring: nearest-neighbour rotation aliasing injects
        # high-frequency energy that otherwise masquerades as sharpness.
        profile = np.convolve(profile, np.ones(7, dtype=np.float32) / 5.0, mode="same")
        # Sharp line boundaries -> high gradient energy of the row profile.
        score = float(np.abs(np.diff(profile)).sum())
        if score > best_score:
            best_score, best_angle = score, float(ang)
    return best_angle


def deskew_pil(pil_img: Image.Image, max_deg: float = 12.0, min_deg: float = 0.35) -> tuple[Image.Image, float]:
    """
    Level the page BEFORE segmentation. Returns (deskewed_image, applied_angle).
    `estimate_skew_tilt` returns the counter-clockwise rotation that levels the
    content, so we apply exactly that angle. Sub-degree tilts are left
    untouched (rotation resampling noise costs more than it fixes).
    """
    bgr = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
    tilt = estimate_skew_tilt(bgr, max_deg=max_deg)
    if abs(tilt) < min_deg:
        return pil_img, 0.0
    h, w = bgr.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), tilt, 1.0)
    rotated = cv2.warpAffine(bgr, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    return Image.fromarray(cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB)), round(float(tilt), 2)


# ---------------------------------------------------------------------------
# Photometric enhancement (light; output stays a natural color image)
# ---------------------------------------------------------------------------

def flatten_illumination(bgr: np.ndarray) -> np.ndarray:
    """Divide by a heavily blurred background estimate to remove shadows and
    uneven lighting (classic document-scanner normalization)."""
    h, w = bgr.shape[:2]
    sigma = max(15.0, max(h, w) / 20.0)
    bg = cv2.GaussianBlur(bgr, (0, 0), sigmaX=sigma)
    flat = cv2.divide(bgr, np.maximum(bg, 1), scale=255)
    return flat


def mild_clahe(bgr: np.ndarray, clip: float = 2.0) -> np.ndarray:
    """Mild CLAHE on the L channel only — contrast boost without artifacts."""
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    lab[..., 0] = clahe.apply(lab[..., 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def light_denoise(bgr: np.ndarray) -> np.ndarray:
    """Conservative colored denoise (slow-ish; disabled by default in config)."""
    return cv2.fastNlMeansDenoisingColored(bgr, None, h=5, hColor=5, templateWindowSize=7, searchWindowSize=15)


def enhance_for_recognition(pil_img: Image.Image, *, flatten: bool = True, clahe: bool = True,
                            denoise: bool = False, clahe_clip: float = 2.0) -> Image.Image:
    """
    Light CPU enhancement for recognition input. Output is still a natural
    color/grayscale-looking image — binarization is deliberately NOT applied
    (harsh black/white inputs measurably degrade VLM/encoder recognition).
    """
    bgr = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
    if flatten:
        bgr = flatten_illumination(bgr)
    if clahe:
        bgr = mild_clahe(bgr, clip=clahe_clip)
    if denoise:
        bgr = light_denoise(bgr)
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


# ---------------------------------------------------------------------------
# Aspect-ratio-preserving letterbox (the core aspect-ratio bug fix)
# ---------------------------------------------------------------------------

@dataclass
class LetterboxResult:
    image: Image.Image
    scale: float        # original -> canvas scale factor
    pad_left: int       # x offset of content inside the canvas
    pad_top: int        # y offset of content inside the canvas
    orig_size: tuple    # (w, h)


def letterbox_square(pil_img: Image.Image, size: int, fill: int = 255, min_content_h: int = 0) -> LetterboxResult:
    """
    Scale the image to fit inside a size x size white canvas, centered.
    When min_content_h > 0 (for TrOCR line crops), prevents extreme aspect-ratio
    shrinking by ensuring the scaled content height is at least min_content_h.
    """
    w, h = pil_img.size
    scale = size / float(max(w, h))
    new_w, new_h = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    if min_content_h > 0 and new_h < min_content_h:
        new_h = min(size, min_content_h)
    resized = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (size, size), (fill, fill, fill))
    pad_left = (size - new_w) // 2
    pad_top = (size - new_h) // 2
    canvas.paste(resized, (pad_left, pad_top))
    return LetterboxResult(image=canvas, scale=scale, pad_left=pad_left, pad_top=pad_top, orig_size=(w, h))


def invert_letterbox_box(box, lb: LetterboxResult, orig_w: int, orig_h: int) -> list:
    """
    Map coordinates from letterboxed canvas space back to original image space.
    Accepts an [x1,y1,x2,y2] box or an 8-value quad [x1,y1,...,x4,y4].
    """
    pts = list(box)

    def inv(x, y):
        ox = (float(x) - lb.pad_left) / max(lb.scale, 1e-6)
        oy = (float(y) - lb.pad_top) / max(lb.scale, 1e-6)
        return min(max(ox, 0.0), float(orig_w)), min(max(oy, 0.0), float(orig_h))

    out = []
    for i in range(0, len(pts), 2):
        ox, oy = inv(pts[i], pts[i + 1])
        out.extend([ox, oy])
    return out


# ---------------------------------------------------------------------------
# Crop helpers
# ---------------------------------------------------------------------------

def prepare_trocr_crop(pil_img: Image.Image, *, input_size: int = 384, letterbox: bool = True,
                       min_text_height: int = 48, min_content_h: int = 110, max_upscale: float = 3.0) -> Image.Image:
    """
    Full preprocessing for one line crop before TrOCR:
      1. (optional) upscale so the ink reaches a readable height on the 384px grid
      2. letterbox onto a white square (aspect preserved with min content height) when enabled
    The TrOCR processor then performs its standard 384x384 resize; because the
    input is already square, the resize no longer distorts glyph shapes.
    """
    img = pil_img.convert("RGB")
    if letterbox:
        ink_h = _estimate_ink_height(np.array(img.convert("L")))
        if 0 < ink_h < min_text_height:
            scale = min(max_upscale, min_text_height / float(ink_h))
            new_size = (max(1, int(round(img.width * scale))), max(1, int(round(img.height * scale))))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        return letterbox_square(img, input_size, min_content_h=min_content_h).image
    return img.resize((input_size, input_size), Image.Resampling.LANCZOS)


def _estimate_ink_height(gray: np.ndarray) -> int:
    """Rough ink height (first..last ink row) used to decide upscaling."""
    if gray.ndim == 3:
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
    thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    rows = thr.sum(axis=1)
    peak = float(rows.max())
    if peak <= 0:
        return 0
    nz = np.nonzero(rows > peak * 0.1)[0]
    return int(nz[-1] - nz[0] + 1) if len(nz) else 0


def split_oversized_bands(bands, profile, *, oversized_ratio: float = 1.5,
                          min_abs_h: int = 90, min_part_h: int = 24,
                          valley_ratio: float = 0.25) -> list:
    """
    Recursively split merged line bands at their deepest internal valley.
    Tightly-spaced handwritten lines otherwise merge into a single band and
    several medications get decoded as one line (a major recall/CER killer).
    `profile` is the smoothed horizontal ink projection over the body rows.
    """
    if not bands:
        return []
    heights = [b - a for (a, b) in bands]
    # Reference line height from the bands that are PROVABLY single short lines
    # (short bands); using the full median fails when short pages list only a
    # few tall merged bands (the median itself becomes the giant band and the
    # threshold never fires — e.g. bands [343,131] kept a 343px 2-line band).
    normal = [h for h in heights if h < min_abs_h]
    if normal:
        reference = float(np.median(normal))
    else:
        # ALL bands are tall (whole page merged into giants): fall back to the
        # physical single-line height (~60px on these pages). The deep-valley
        # guard below still protects genuinely continuous tall lines.
        reference = 60.0
    threshold_h = max(oversized_ratio * reference, float(min_abs_h))

    result = []
    stack = [tuple(band) for band in bands]
    while stack:
        a, b = stack.pop(0)
        if (b - a) > threshold_h and (b - a) >= 2 * min_part_h:
            seg = np.asarray(profile[a:b], dtype=np.float32)
            inner = seg[min_part_h:-min_part_h] if seg.size > 2 * min_part_h else seg[:0]
            if inner.size:
                v_rel = int(np.argmin(inner))
                cut = a + min_part_h + v_rel
                valley, peak = float(inner[v_rel]), float(seg.max())
                if peak > 0 and valley < valley_ratio * peak:
                    stack.insert(0, (cut, b))
                    stack.insert(0, (a, cut))
                    continue
        result.append((int(a), int(b)))
    result.sort()
    return result


def pad_left_white(pil_img: Image.Image, ratio: float) -> Image.Image:
    """
    Add a white margin of `ratio` * width to the LEFT of a line crop.
    Used by the low-confidence retry: TrOCR most often drops the first glyph
    of a line, and an explicit white runway before the first stroke lets the
    decoder commit to it.
    """
    if ratio <= 0:
        return pil_img
    w, h = pil_img.size
    extra = max(1, int(round(w * ratio)))
    canvas = Image.new("RGB", (w + extra, h), (255, 255, 255))
    canvas.paste(pil_img, (extra, 0))
    return canvas


def ink_x_bounds(band_bgr: np.ndarray) -> tuple[int, int] | None:
    """
    Horizontal extent of actual ink inside a line band (used to replace the
    fixed 5%-95% page-width crop so word starts/ends are never cut).
    Returns (x0, x1) in band coordinates, or None when no ink is found.
    """
    gray = cv2.cvtColor(band_bgr, cv2.COLOR_BGR2GRAY)
    thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    cols = thr.sum(axis=0).astype(np.float32)
    k = max(3, int(band_bgr.shape[1] // 80) | 1)
    smooth = np.convolve(cols, np.ones(k, dtype=np.float32) / k, mode="same")
    peak = float(smooth.max())
    if peak <= 0:
        return None
    nz = np.where(smooth >= max(2.0, peak * 0.12))[0]
    if len(nz) == 0:
        return None
    return int(nz[0]), int(nz[-1])
