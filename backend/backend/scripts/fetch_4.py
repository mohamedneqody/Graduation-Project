from pathlib import Path
from icrawler.builtin import BingImageCrawler
import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv('d:\\Graduation Project\\backend\\backend\\.env')
url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')
FRONTEND_IMAGES_DIR = Path(r"d:\Graduation Project\stitch_ai_cos_pharmacy\ai-cos-frontend\public\drug-images")

drugs = [
    "Amaryl 2mg",
    "Amlopres 5mg",
    "Augmentin 1g"
]
# Amoclan was already downloaded successfully!

async def update_db(name, img_url):
    conn = await asyncpg.connect(url)
    await conn.execute('UPDATE drugs SET image_url = $1 WHERE name ILIKE $2', img_url, '%' + name.split()[0] + '%')
    print(f'Updated {name} to {img_url}')
    await conn.close()

def fetch():
    for name in drugs:
        print(f"Searching for {name}...")
        crawler = BingImageCrawler(storage={'root_dir': str(FRONTEND_IMAGES_DIR)})
        before = set(os.listdir(FRONTEND_IMAGES_DIR))
        crawler.crawl(keyword=f"{name} medicine box egypt", max_num=1)
        after = set(os.listdir(FRONTEND_IMAGES_DIR))
        new_files = after - before
        
        if new_files:
            new_file = new_files.pop()
            ext = new_file.split('.')[-1]
            slug = name.split()[0].lower()
            new_name = f"{slug}.{ext}"
            
            old_path = FRONTEND_IMAGES_DIR / new_file
            new_path = FRONTEND_IMAGES_DIR / new_name
            
            if new_path.exists():
                new_path.unlink()
                
            old_path.rename(new_path)
            
            new_url = f"/drug-images/{new_name}"
            asyncio.run(update_db(name, new_url))
            print(f" -> Saved {new_name}")
        else:
            print(f" -> Failed to find image for {name}")

if __name__ == "__main__":
    fetch()
