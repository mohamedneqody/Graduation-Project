import httpx
import asyncio

async def test_scraping():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        print("Testing Chefaa...")
        try:
            r = await client.get("https://chefaa.com/")
            print(f"Chefaa Status: {r.status_code}")
        except Exception as e:
            print(f"Chefaa Error: {e}")
            
        print("\nTesting Seif Pharmacy...")
        try:
            r = await client.get("https://seifpharmacy.com/")
            print(f"Seif Status: {r.status_code}")
        except Exception as e:
            print(f"Seif Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_scraping())
