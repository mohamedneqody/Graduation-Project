import asyncio
import os
import re
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

async def test_scrape():
    url = os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Missing Supabase credentials!")
        return

    # Use HTTPX directly for Supabase storage API to avoid version conflicts if supabase-py acts up
    storage_base_url = f"{url}/storage/v1"
    headers = {
        "Authorization": f"Bearer {key}",
        "apikey": key
    }
    
    async with httpx.AsyncClient() as client:
        # Check if bucket exists
        resp = await client.get(f"{storage_base_url}/bucket/drug-images", headers=headers)
        if resp.status_code == 404:
            # Create bucket
            print("Creating bucket 'drug-images'...")
            await client.post(
                f"{storage_base_url}/bucket",
                headers=headers,
                json={"id": "drug-images", "name": "drug-images", "public": True}
            )
        else:
            # Ensure it's public
            await client.put(
                f"{storage_base_url}/bucket/drug-images",
                headers=headers,
                json={"id": "drug-images", "name": "drug-images", "public": True}
            )
            print("Bucket 'drug-images' verified and is public.")

        # Scrape DawaaGate
        print("\nFetching DawaaGate cardiovascular category...")
        scrape_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        target_url = "https://www.dawaagate.com/category/cardiovascular"
        resp = await client.get(target_url, headers=scrape_headers)
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        cards = soup.find_all('article', class_='ph-card')
        
        results = []
        
        print(f"Found {len(cards)} cards. Extracting up to 12...")
        
        for i, card in enumerate(cards[:12]):
            en_name_el = card.find('p', class_='ph-card-en')
            price_el = card.find('span', class_='ph-price-now')
            img_el = card.find('img', class_='ph-card-img')
            
            if not en_name_el or not price_el or not img_el:
                continue
                
            en_name = en_name_el.get_text(strip=True)
            price_str = price_el.get_text(strip=True)
            try:
                price = float(price_str)
            except:
                price = 0.0
                
            img_src = img_el.get('src') or img_el.get('data-src')
            if not img_src:
                continue
                
            # Create clean filename
            safe_name = re.sub(r'[^a-zA-Z0-9-]', '-', en_name).strip('-').lower()
            safe_name = re.sub(r'-+', '-', safe_name)
            filename = f"{safe_name}.webp"
            
            # Download image
            print(f"Downloading image for {en_name}...")
            img_resp = await client.get(img_src, headers=scrape_headers)
            if img_resp.status_code == 200:
                # Upload to Supabase
                print(f"Uploading {filename} to Supabase...")
                upload_resp = await client.post(
                    f"{storage_base_url}/object/drug-images/{filename}",
                    headers={**headers, "Content-Type": "image/webp"},
                    content=img_resp.content
                )
                
                # Public URL
                public_url = f"{url}/storage/v1/object/public/drug-images/{filename}"
                
                results.append({
                    "name": en_name,
                    "price": price,
                    "category": "مزمن - ضغط",
                    "image_url": public_url
                })
                
            # Add delay
            await asyncio.sleep(1.5)
            
    # Generate markdown report
    report = "# تقرير اختبار DawaaGate (12 دواء - Cardiovascular)\n\n"
    report += "| الاسم | السعر | التصنيف | الصورة |\n"
    report += "|---|---|---|---|\n"
    
    for r in results:
        report += f"| {r['name']} | {r['price']} | {r['category']} | ![صورة الدواء]({r['image_url']}) |\n"
        
    report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".gemini", "antigravity", "brain", "f060737c-82d1-4ac6-967a-2c159f8a03b1", "dawaagate_test_report.md"))
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"\nTest complete! Saved report to {report_path}")

if __name__ == "__main__":
    asyncio.run(test_scrape())
