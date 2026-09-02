import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine('postgresql+asyncpg://postgres.quhfheudhewxqmvxwjij:010184333028686@aws-0-eu-central-1.pooler.supabase.com:5432/postgres')
    
    print("| Medicine | DB image_url | Expected file | File exists? |")
    print("|---|---|---|---|")
    
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT name, image_url FROM drugs ORDER BY name LIMIT 20"))
        
        frontend_dir = r"d:\Graduation Project\stitch_ai_cos_pharmacy\ai-cos-frontend"
        
        for row in res.fetchall():
            name = row[0]
            db_url = row[1]
            
            if db_url and db_url.startswith("/"):
                # expected relative path: public\drug-images\xxx
                expected_rel = f"public{db_url.replace('/', '\\')}"
                expected_abs = os.path.join(frontend_dir, expected_rel)
                exists = os.path.exists(expected_abs)
                exists_str = "YES" if exists else "NO"
                print(f"| {name} | {db_url} | {expected_rel.replace(chr(92), '/')} | {exists_str} |")
            else:
                print(f"| {name} | {db_url} | N/A | NO |")

asyncio.run(main())
