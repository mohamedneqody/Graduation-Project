import httpx
from app.core.config import settings
import asyncio
import base64

async def test_model(model_name):
    async with httpx.AsyncClient(timeout=30) as client:
        # Create a valid tiny image (1x1 transparent GIF)
        tiny_gif = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
        b64_data = base64.b64encode(tiny_gif).decode("utf-8")
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "image/gif",
                                "data": b64_data
                            }
                        },
                        {
                            "text": "What is this image?"
                        }
                    ]
                }
            ]
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
        print(f"Testing {model_name}...")
        resp = await client.post(url, json=payload)
        print(f"Status: {resp.status_code}")
        if resp.status_code != 200:
            print(resp.text)

async def main():
    await test_model("gemini-3.7-flash")
    await asyncio.sleep(2)
    await test_model("gemini-3.5-flash")

asyncio.run(main())
