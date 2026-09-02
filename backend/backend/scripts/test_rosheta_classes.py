import httpx
from bs4 import BeautifulSoup
import asyncio

async def test_rosheta():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        r = await client.get("https://www.rosheta.com/en/search?q=panadol")
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Look for any links with 'item' or 'product' or 'medicine'
        medicines = soup.find_all("div", class_="medicine-details")
        print(f"Found {len(medicines)} medicines")
        if not medicines:
            # print all div classes
            classes = set()
            for div in soup.find_all("div"):
                if div.get("class"):
                    classes.update(div.get("class"))
            print("Classes:", classes)
        else:
            for m in medicines[:3]:
                print(m.text.strip())

if __name__ == "__main__":
    asyncio.run(test_rosheta())
