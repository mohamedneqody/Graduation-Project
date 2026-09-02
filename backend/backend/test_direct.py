import httpx
from app.core.config import settings
import asyncio
import base64

async def main():
    async with httpx.AsyncClient() as client:
        # Create a dummy payload matching vision.py
        b64_data = base64.b64encode(b"dummy image data").decode("utf-8")
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
                "parts": [{"text": "You are a prescription-reading assistant"}]
            },
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": b64_data
                            }
                        },
                        {
                            "text": "Transcribe this prescription"
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
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.7-flash:generateContent?key={settings.GEMINI_API_KEY}"
        resp = await client.post(url, json=payload)
        print(resp.status_code)
        print(resp.text)

asyncio.run(main())
