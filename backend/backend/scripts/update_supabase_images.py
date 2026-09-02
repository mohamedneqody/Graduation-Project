import asyncio
import asyncpg
from pathlib import Path
import os
from dotenv import load_dotenv

env_path = Path(r"d:\Graduation Project\backend\backend\.env")
load_dotenv(env_path)

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

FRONTEND_IMAGES_DIR = Path(r"d:\Graduation Project\stitch_ai_cos_pharmacy\ai-cos-frontend\public\drug-images")

async def update_db():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT name, image_url FROM drugs")
    updated = 0
    for row in rows:
        slug = row['name'].lower().replace(' ', '-').replace('/', '-').replace('(', '').replace(')', '')
        # check if there's any file matching slug.*
        matches = list(FRONTEND_IMAGES_DIR.glob(f"{slug}.*"))
        if matches:
            ext = matches[0].suffix
            new_url = f"/drug-images/{slug}{ext}"
            if row['image_url'] != new_url:
                await conn.execute("UPDATE drugs SET image_url = $1 WHERE name = $2", new_url, row['name'])
                updated += 1
                print(f"Updated {row['name']} -> {new_url}")
    await conn.close()
    print(f"Total updated: {updated}")

if __name__ == "__main__":
    asyncio.run(update_db())
