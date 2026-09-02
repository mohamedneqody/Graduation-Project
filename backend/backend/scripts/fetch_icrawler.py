import asyncio
import asyncpg
from pathlib import Path
from icrawler.builtin import BingImageCrawler
import os

DB_URL = "postgresql://postgres:postgres@localhost:5432/ai_cos_pharmacy"
FRONTEND_IMAGES_DIR = Path(r"d:\Graduation Project\stitch_ai_cos_pharmacy\ai-cos-frontend\public\drug-images")

async def get_missing_drugs():
    conn = await asyncpg.connect(DB_URL)
    rows = await conn.fetch("SELECT id, name, image_url, category FROM drugs")
    missing = []
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
            missing.append(dict(row))
    await conn.close()
    return missing

async def update_db_url(drug_id, new_url):
    conn = await asyncpg.connect(DB_URL)
    await conn.execute("UPDATE drugs SET image_url = $1 WHERE id = $2", new_url, drug_id)
    await conn.close()

def fetch_images():
    missing = asyncio.run(get_missing_drugs())
    print(f"Found {len(missing)} missing drugs.")
    
    for drug in missing:
        query = f"{drug['name']} {drug['category']} medicine box egypt"
        print(f"Searching for: {query}")
        
        crawler = BingImageCrawler(storage={'root_dir': str(FRONTEND_IMAGES_DIR)})
        # It names files 000001.jpg etc. So we need to find the latest file downloaded
        before = set(os.listdir(FRONTEND_IMAGES_DIR))
        crawler.crawl(keyword=query, max_num=1)
        after = set(os.listdir(FRONTEND_IMAGES_DIR))
        new_files = after - before
        
        if new_files:
            new_file = new_files.pop()
            # Rename it to drug slug
            ext = new_file.split('.')[-1]
            slug = drug['name'].lower().replace(' ', '-').replace('/', '-').replace('(', '').replace(')', '')
            new_name = f"{slug}.{ext}"
            
            old_path = FRONTEND_IMAGES_DIR / new_file
            new_path = FRONTEND_IMAGES_DIR / new_name
            
            if new_path.exists():
                new_path.unlink()
                
            old_path.rename(new_path)
            
            new_url = f"/drug-images/{new_name}"
            asyncio.run(update_db_url(drug['id'], new_url))
            print(f" -> Saved {new_name}")
        else:
            print(f" -> Failed to find image for {drug['name']}")

if __name__ == "__main__":
    fetch_images()
