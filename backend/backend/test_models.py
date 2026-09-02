import httpx
from app.core.config import settings
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={settings.GEMINI_API_KEY}")
        models = r.json()
        for m in models.get('models', []):
            if 'flash' in m['name']:
                print(m['name'])

asyncio.run(main())
