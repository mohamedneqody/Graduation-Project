import asyncio
import asyncpg
from duckduckgo_search import DDGS
import os
from dotenv import load_dotenv
import httpx
import re
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / '.env')
DB_URL = os.getenv('DATABASE_URL')
if DB_URL and DB_URL.startswith('postgresql+asyncpg://'):
    DB_URL = DB_URL.replace('postgresql+asyncpg://', 'postgresql://')

FRONTEND_IMAGES_DIR = Path(r"d:\Graduation Project\stitch_ai_cos_pharmacy\ai-cos-frontend\public\drug-images")

def make_slug(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

async def fetch_image_for_drug(drug_id, drug_name, conn, httpx_client):
    try:
        ddgs = DDGS()
        query = f"{drug_name} medicine box egypt"
        print(f"Searching for {query}...")
        
        results = list(ddgs.images(query, max_results=1))
        
        if not results:
            print(f"  [!] No image found for {drug_name}")
            return
            
        img_url = results[0]['image']
        print(f"  Found URL: {img_url}")
        
        try:
            resp = await httpx_client.get(img_url, timeout=10)
            if resp.status_code != 200:
                print(f"  [!] Failed to download, status {resp.status_code}")
                return
                
            ext = '.jpg'
            content_type = resp.headers.get('content-type', '').lower()
            if 'png' in content_type: ext = '.png'
            elif 'webp' in content_type: ext = '.webp'
            elif 'jpeg' in content_type or 'jpg' in content_type: ext = '.jpg'
            else:
                if '.png' in img_url.lower(): ext = '.png'
                elif '.webp' in img_url.lower(): ext = '.webp'
                
            slug = make_slug(drug_name)
            filename = f"{slug}{ext}"
            filepath = FRONTEND_IMAGES_DIR / filename
            
            with open(filepath, 'wb') as f:
                f.write(resp.content)
                
            db_path = f"/drug-images/{filename}"
            await conn.execute("UPDATE drugs SET image_url = $1 WHERE drug_id = $2", db_path, drug_id)
            print(f"  [+] Saved {filename} and updated DB!")
            
        except Exception as e:
            print(f"  [!] Error downloading image for {drug_name}: {e}")
            
    except Exception as e:
        print(f"  [!] DDGS error for {drug_name}: {e}")

async def main():
    FRONTEND_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    conn = await asyncpg.connect(DB_URL)
    
    rows = await conn.fetch("SELECT drug_id, name, image_url FROM drugs")
    
    missing_drugs = []
    for row in rows:
        url = row['image_url']
        is_missing = False
        if not url or url == 'null':
            is_missing = True
        else:
            filename = url.split('/')[-1]
            filepath = FRONTEND_IMAGES_DIR / filename
            if not filepath.exists():
                is_missing = True
                
        if is_missing:
            missing_drugs.append(row)
            
    print(f"Found {len(missing_drugs)} drugs whose images don't exist locally.")
    
    async with httpx.AsyncClient() as httpx_client:
        for row in missing_drugs:
            await fetch_image_for_drug(row['drug_id'], row['name'], conn, httpx_client)
            await asyncio.sleep(1.5)
            
    await conn.close()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
