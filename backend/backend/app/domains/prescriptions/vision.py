import httpx
import base64
from typing import List, Optional
import pydantic
from app.core.config import settings

class MedicationItem(pydantic.BaseModel):
    raw_name: Optional[str] = None
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    quantity: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None
    ocr_confidence: float
    is_illegible: bool

class PrescriptionVisionOutput(pydantic.BaseModel):
    medications: List[MedicationItem]
    image_quality_notes: Optional[str] = None

class VisionMetadata(pydantic.BaseModel):
    model_version: Optional[str] = None
    prompt_version: Optional[str] = None
    request_id: Optional[str] = None
    latency_ms: Optional[int] = None
    token_usage: Optional[dict] = None

class PrescriptionVisionService:
    async def analyze_image(self, file_bytes: bytes, mime_type: str) -> tuple[PrescriptionVisionOutput, VisionMetadata]:
        raise NotImplementedError

class GeminiVisionProvider(PrescriptionVisionService):
    def __init__(self):
        # We use gemini-3.7-flash for stability (GA status, no announced shutdown date)
        # instead of a Pro preview model. This was NOT a benchmark-driven accuracy decision.
        # Accuracy must still be validated against the Phase 0 dataset (30-50 real Egyptian 
        # prescriptions) and may require switching back to a Pro-tier model if too low.
        self.model = getattr(settings, "GEMINI_MODEL", "gemini-3.7-flash")
        self.api_key = settings.GEMINI_API_KEY
        self.timeout = 60.0  # Increased from 15.0 to handle larger images
        self.prompt_version = "v1.0"

    async def analyze_image(self, file_bytes: bytes, mime_type: str = "image/jpeg") -> tuple[PrescriptionVisionOutput, VisionMetadata]:
        import time
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        system_prompt = """You are a prescription-reading assistant embedded in a pharmacy backend system.
Your ONLY job is to transcribe what is written on the prescription image as
accurately as possible. You do NOT decide which real product this corresponds
to, you do NOT guess missing information, and you do NOT complete or correct
drug names based on what you think the doctor "probably meant."

Rules:
1. Extract exactly what is visually present. If handwriting is ambiguous,
   transcribe your best reading and lower ocr_confidence accordingly — do not
   silently "fix" it into a known drug name.
2. If a field is not present or not legible, set it to null. Do NOT infer it.
3. If a whole line is illegible, still include it with raw_name as your best
   partial guess (or null if nothing is readable) and mark is_illegible: true.
4. Never output any drug name, strength, or instruction that does not
   correspond to something actually visible in the image.
5. If a name is visually clear but does not match any word you expect, do
   NOT "correct" its spelling — transcribe exactly what is written.
6. If multiple readings of the same handwriting are plausible, do not silently
   pick one. Lower ocr_confidence and set is_illegible: true instead of
   guessing.
7. Return ONLY the fields defined by the response schema. No extra
   commentary fields, no markdown, no code fences.

Output schema (also enforced structurally via response_schema, not just
described here):
{
  "medications": [
    {
      "raw_name": string | null,
      "strength": string | null,
      "dosage_form": string | null,
      "quantity": string | null,
      "duration": string | null,
      "instructions": string | null,
      "ocr_confidence": number,
      "is_illegible": boolean
    }
  ],
  "image_quality_notes": string | null
}"""

        b64_data = base64.b64encode(file_bytes).decode("utf-8")
        
        # Gemini requires a specific OpenAPI-like schema format without $refs
        gemini_schema = {
            "type": "OBJECT",
            "properties": {
                "medications": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "raw_name": {"type": "STRING"},
                            "strength": {"type": "STRING"},
                            "dosage_form": {"type": "STRING"},
                            "quantity": {"type": "STRING"},
                            "duration": {"type": "STRING"},
                            "instructions": {"type": "STRING"},
                            "ocr_confidence": {"type": "NUMBER"},
                            "is_illegible": {"type": "BOOLEAN"}
                        },
                        "required": ["ocr_confidence", "is_illegible"]
                    }
                },
                "image_quality_notes": {"type": "STRING"}
            },
            "required": ["medications"]
        }

        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_data
                            }
                        },
                        {
                            "text": "Transcribe this prescription following the system rules strictly."
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": gemini_schema,
                "temperature": 0.0
            }
        }
        
        models_to_try = [self.model, "gemini-3.5-flash"]
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt, current_model in enumerate(models_to_try):
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={self.api_key}"
                try:
                    start_time = time.time()
                    resp = await client.post(url, json=payload)
                    latency_ms = int((time.time() - start_time) * 1000)
                    
                    if resp.status_code == 503 and attempt == 0:
                        import asyncio
                        await asyncio.sleep(1) # Small backoff before trying fallback
                        continue
                        
                    resp.raise_for_status()
                    data = resp.json()
                    
                    text_result = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = PrescriptionVisionOutput.model_validate_json(text_result)
                    
                    metadata = VisionMetadata(
                        model_version=data.get("modelVersion", current_model),
                        prompt_version=self.prompt_version,
                        request_id=resp.headers.get("x-goog-request-id", ""),
                        latency_ms=latency_ms,
                        token_usage=data.get("usageMetadata", {})
                    )
                    return parsed, metadata
                except httpx.ReadTimeout:
                    if attempt == 0:
                        continue
                    raise Exception(f"Vision API timeout after trying {current_model}")
                except Exception as e:
                    if attempt == 0:
                        continue
                    raise e
