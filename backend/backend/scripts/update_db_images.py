import asyncio, asyncpg, os, re
from dotenv import load_dotenv

load_dotenv(r"d:\Graduation Project\backend\backend\.env")
out_dir = r"d:\Graduation Project\stitch_ai_cos_pharmacy\ai-cos-frontend\public\drug-images"

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")

async def update_db():
    db_url = os.environ["DATABASE_URL"].replace("+asyncpg", "")
    conn = await asyncpg.connect(db_url)
    rows = await conn.fetch("SELECT drug_id, name FROM drugs")
    
    updated = 0
    for row in rows:
        slug = slugify(row["name"])
        
        webp_path = os.path.join(out_dir, f"{slug}.webp")
        jpg_path = os.path.join(out_dir, f"{slug}.jpg")
        png_path = os.path.join(out_dir, f"{slug}.png")
        
        final_url = None
        if os.path.exists(webp_path):
            final_url = f"/drug-images/{slug}.webp"
        elif os.path.exists(jpg_path):
            final_url = f"/drug-images/{slug}.jpg"
        elif os.path.exists(png_path):
            final_url = f"/drug-images/{slug}.png"
            
        if final_url:
            await conn.execute("UPDATE drugs SET image_url = $1 WHERE drug_id = $2", final_url, row["drug_id"])
            updated += 1
            
    print(f"Updated {updated} records in the database with real image URLs.")
    await conn.close()

asyncio.run(update_db())
