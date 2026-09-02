import httpx
from bs4 import BeautifulSoup
import asyncio

async def test_dawaya():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        r = await client.get("https://tablet.com.eg/search.php?q=panadol")
        print("Tablet status:", r.status_code)
        print("Tablet length:", len(r.text))
        soup = BeautifulSoup(r.text, 'html.parser')
        products = soup.find_all("div", class_="product")
        print(f"Found {len(products)} products on Tablet")
        
        # let's try to just find any images
        imgs = soup.find_all("img")
        print(f"Found {len(imgs)} images on Tablet")

if __name__ == "__main__":
    asyncio.run(test_dawaya())
