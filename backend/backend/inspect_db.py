import asyncio
import sys
import json
from app.database.session import AsyncSessionLocal
from sqlalchemy import text

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with AsyncSessionLocal() as session:
        print("=== SAMPLE DRUG RECORDS ===")
        drug_res = await session.execute(text('SELECT drug_id, name, category, is_chronic, base_price, default_cycle_days, image_url FROM drugs LIMIT 10;'))
        for row in drug_res.fetchall():
            d = dict(row._mapping)
            d['drug_id'] = str(d['drug_id'])
            d['base_price'] = float(d['base_price'])
            print(json.dumps(d, ensure_ascii=False))
            
        print("\n=== DISTINCT DRUG CATEGORIES ===")
        cat_res = await session.execute(text('SELECT category, COUNT(*) as count FROM drugs GROUP BY category ORDER BY count DESC;'))
        for row in cat_res.fetchall():
            print(json.dumps(dict(row._mapping), ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
