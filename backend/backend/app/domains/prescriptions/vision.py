"""On-premise-only adapter for the prescription OCR microservice.

Prescription images are PHI. This module deliberately has no cloud vision
provider and fails closed if the loopback OCR service is unavailable.
"""

import time
from typing import Any, List, Optional

import httpx
import pydantic

from app.core.config import settings


class MedicationItem(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="ignore")
    line_number: Optional[int] = None
    raw_name: Optional[str] = pydantic.Field(default=None, max_length=255)
    strength: Optional[str] = pydantic.Field(default=None, max_length=100)
    dosage_form: Optional[str] = pydantic.Field(default=None, max_length=100)
    quantity: Optional[str] = pydantic.Field(default=None, max_length=50)
    duration: Optional[str] = pydantic.Field(default=None, max_length=50)
    instructions: Optional[str] = pydantic.Field(default=None, max_length=500)
    ocr_confidence: float = pydantic.Field(default=0.0, ge=0.0, le=1.0)
    # v4.1: real per-model confidences (decoder log-prob derived). Kept for
    # auditability; ocr_confidence remains the fused gate used by matching.
    trocr_confidence: Optional[float] = None
    florence_confidence: Optional[float] = None
    is_illegible: bool = False
    is_fragment_too_short: bool = False
    visual_style: str = "unknown"
    visual_evidence_ok: bool = False
    model_disagreement: bool = False
    trocr_text: Optional[str] = None
    florence_text: Optional[str] = None
    bbox: Optional[list[int]] = None
    cropped_image: Optional[str] = None


class ImageFingerprint(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="ignore")
    sha256: Optional[str] = None
    top_left_visible_text: Optional[str] = None
    clinic_name_guess: Optional[str] = None
    patient_name_guess: Optional[str] = None
    approximate_image_orientation: Optional[str] = None
    number_of_handwritten_lines_visible: Optional[int] = 0


class PrescriptionVisionOutput(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="ignore")
    image_fingerprint: Optional[ImageFingerprint] = None
    pipeline_hashes: dict[str, Optional[str]] = pydantic.Field(default_factory=dict)
    medications: List[MedicationItem]
    excluded_header_lines: List[str] = pydantic.Field(default_factory=list)
    rejected_phantom_candidates: List[str] = pydantic.Field(default_factory=list)
    image_quality_notes: Optional[str] = None


class VisionMetadata(pydantic.BaseModel):
    model_version: Optional[str] = None
    prompt_version: Optional[str] = None
    request_id: Optional[str] = None
    latency_ms: Optional[int] = None
    token_usage: Optional[dict[str, Any]] = None


class PrescriptionVisionService:
    async def analyze_image(
        self, file_bytes: bytes, mime_type: str
    ) -> tuple[PrescriptionVisionOutput, VisionMetadata]:
        raise NotImplementedError


class LocalTrOCRVisionProvider(PrescriptionVisionService):
    """Calls Florence-2 + TrOCR on 127.0.0.1 only."""

    model = "florence-2-base-ft+trocr-finetuned-final"

    def __init__(self) -> None:
        self.endpoint = settings.LOCAL_OCR_URL.rstrip("/") + "/api/infer-text"
        self.timeout = settings.LOCAL_OCR_TIMEOUT
        self.internal_secret = settings.INTERNAL_OCR_SECRET
        if not self.internal_secret:
            raise RuntimeError("INTERNAL_OCR_SECRET is required for local OCR authentication.")

    async def analyze_image(
        self, file_bytes: bytes, mime_type: str = "image/jpeg"
    ) -> tuple[PrescriptionVisionOutput, VisionMetadata]:
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.endpoint,
                    files={"file": ("prescription", file_bytes, mime_type)},
                    headers={"X-Internal-Secret": self.internal_secret},
                )
            response.raise_for_status()
            output = PrescriptionVisionOutput.model_validate(response.json())
        except (httpx.HTTPError, ValueError, pydantic.ValidationError) as exc:
            raise RuntimeError("Local OCR service is unavailable or returned an invalid response") from exc

        return output, VisionMetadata(
            model_version=self.model,
            prompt_version="v4.1-strict-local",
            request_id=response.headers.get("x-request-id", "local-ocr"),
            latency_ms=int((time.perf_counter() - started) * 1000),
            token_usage=None,
        )
