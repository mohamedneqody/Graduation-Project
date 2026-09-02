import asyncio, asyncpg, os, uuid
import pandas as pd
from dotenv import load_dotenv

load_dotenv('d:\\Graduation Project\\backend\\backend\\.env')
url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')

async def main():
    csv_path = r'C:\Users\zbook\Downloads\dawaagate_medicines_MERGED_FINAL (1).csv'
    df_csv = pd.read_csv(csv_path)
    
    conn = await asyncpg.connect(url)
    inserted = 0
    for idx, row in df_csv.iterrows():
        name = row['name']
        img = row.get('image_url')
        if pd.notna(img) and str(img).strip() != '' and str(img).strip() != 'null':
            exists = await conn.fetchval('SELECT 1 FROM drugs WHERE name = $1', name)
            if not exists:
                drug_id = str(uuid.uuid4())
                await conn.execute('''
                    INSERT INTO drugs (drug_id, name, category, is_chronic, base_price, default_cycle_days, image_url)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                ''', 
                drug_id, 
                name, 
                row.get('category'), 
                row.get('is_chronic') == True or str(row.get('is_chronic')).lower() == 'true',
                float(row.get('base_price', 0) if pd.notna(row.get('base_price')) else 0),
                int(row.get('default_cycle_days', 30) if pd.notna(row.get('default_cycle_days')) else 30),
                str(img))
                inserted += 1
                
    print(f'Inserted {inserted} missing drugs into the database.')
    await conn.close()

asyncio.run(main())
