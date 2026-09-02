import asyncio
import asyncpg
import os
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv('d:\\Graduation Project\\backend\\backend\\.env')
url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')
FRONTEND_IMAGES_DIR = Path(r"d:\Graduation Project\stitch_ai_cos_pharmacy\ai-cos-frontend\public\drug-images")

# Real images from public sources for these specific 4 drugs
images = {
    'Amaryl': 'https://www.medica-tradefairs.com/exh_mda/mob/exh_mda/mob_image_item_7423018.jpg',
    'Amlopres': 'https://almasrypharmacy.com/wp-content/uploads/2021/04/AMLOPRES-5MG-30-TAB.jpg',
    'Amoclan': 'https://seif-online.com/wp-content/uploads/2019/11/Amoclan-1-gm-14-tab-1.jpg',
    'Augmentin': 'https://chefaa.com/images/products/augmentin-1gm-14-tablets-wmsq.jpeg'
}

async def fix_images():
    conn = await asyncpg.connect(url)
    for name, img_url in images.items():
        # Download image
        ext = img_url.split('.')[-1]
        slug = name.lower()
        filename = f"{slug}.{ext}"
        filepath = FRONTEND_IMAGES_DIR / filename
        
        print(f"Downloading {name} from {img_url}...")
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(img_url, headers=headers)
            res.raise_for_status()
            with open(filepath, 'wb') as f:
                f.write(res.content)
            
            db_url = f"/drug-images/{filename}"
            await conn.execute('UPDATE drugs SET image_url = $1 WHERE name ILIKE $2', db_url, '%' + name + '%')
            print(f'Updated {name} in DB to {db_url}')
        except Exception as e:
            print(f"Error for {name}: {e}")
            
    await conn.close()

asyncio.run(fix_images())
