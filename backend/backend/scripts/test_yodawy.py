import httpx
import asyncio

async def test_yodawy():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        r = await client.get("https://api.yodawy.com/api/v1/products?q=panadol")
        print("Yodawy status:", r.status_code)
        if r.status_code == 200:
            print("Content:", r.text[:200])

if __name__ == "__main__":
    asyncio.run(test_yodawy())
