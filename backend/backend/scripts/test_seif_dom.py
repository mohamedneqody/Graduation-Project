import httpx
from bs4 import BeautifulSoup
import asyncio

async def test_seif():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        r = await client.get("https://seifpharmacy.com/en/")
        print("Length of Seif HTML:", len(r.text))
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Look for product links
        for a in soup.find_all("a", href=True):
            if "product" in a['href'] or "item" in a['href']:
                print("Found link:", a['href'])

if __name__ == "__main__":
    asyncio.run(test_seif())
