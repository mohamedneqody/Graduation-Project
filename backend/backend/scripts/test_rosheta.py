import httpx
from bs4 import BeautifulSoup
import asyncio

async def test_rosheta():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        r = await client.get("https://www.rosheta.com/en/search?q=panadol")
        print("Rosheta length:", len(r.text))
        soup = BeautifulSoup(r.text, 'html.parser')
        products = soup.find_all("div", class_="product-item")
        print(f"Found {len(products)} products on Rosheta")
        if products:
            print(products[0].text.strip())

if __name__ == "__main__":
    asyncio.run(test_rosheta())
