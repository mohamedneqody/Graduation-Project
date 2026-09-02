import httpx
from bs4 import BeautifulSoup
import asyncio

async def test_chefaa():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        r = await client.get("https://chefaa.com/search?q=%D8%B6%D8%BA%D8%B7") # "ضغط"
        soup = BeautifulSoup(r.text, 'html.parser')
        products = soup.find_all("div", class_="product-card")
        
        if not products:
            print("No 'product-card' found, trying other common classes...")
            for div in soup.find_all("div")[:20]:
                if div.get("class") and "product" in str(div.get("class")):
                    print(div.get("class"))
        else:
            for p in products[:3]:
                print(p.text.strip())

if __name__ == "__main__":
    asyncio.run(test_chefaa())
