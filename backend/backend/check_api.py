import httpx
import asyncio

async def fetch():
    async with httpx.AsyncClient() as client:
        r = await client.get('http://127.0.0.1:8000/api/v1/inventory?limit=12&offset=0', headers={'X-Tenant-ID': '62712616-be1e-4129-986f-4131877e63b8'})
        items = r.json().get('items', [])
        for p in items:
            print(f"{p.get('name')}: {p.get('image_url')}")

asyncio.run(fetch())
