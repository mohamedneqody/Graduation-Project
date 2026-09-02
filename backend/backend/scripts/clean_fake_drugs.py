import asyncio
import asyncpg
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv('d:\\Graduation Project\\backend\\backend\\.env')
url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')

async def clean_db():
    conn = await asyncpg.connect(url)
    
    # Read the original CSV
    df = pd.read_csv('C:\\Users\\zbook\\Downloads\\dawaagate_medicines_MERGED_FINAL (1).csv')
    
    # Get names of drugs that had a valid image_url
    valid_names = []
    for idx, row in df.iterrows():
        img = row['image_url']
        name = row['name']
        if pd.notna(img) and str(img).strip() != '' and str(img).strip() != 'null':
            valid_names.append(name)
            
    # Also restore their images just in case
    print(f"Found {len(valid_names)} valid drugs in the original CSV.")
    
    # Delete everything that is NOT in the valid list
    deleted = 0
    res = await conn.fetch('SELECT name FROM drugs')
    db_names = [r['name'] for r in res]
    
    for db_name in db_names:
        if db_name not in valid_names:
            await conn.execute('DELETE FROM drug_interactions WHERE drug_id_a IN (SELECT drug_id FROM drugs WHERE name = $1) OR drug_id_b IN (SELECT drug_id FROM drugs WHERE name = $1)', db_name)
            await conn.execute('DELETE FROM customer_cycles WHERE drug_id IN (SELECT drug_id FROM drugs WHERE name = $1)', db_name)
            await conn.execute('DELETE FROM drug_affinities WHERE drug_id_a IN (SELECT drug_id FROM drugs WHERE name = $1) OR drug_id_b IN (SELECT drug_id FROM drugs WHERE name = $1)', db_name)
            await conn.execute('DELETE FROM order_items WHERE drug_id IN (SELECT drug_id FROM drugs WHERE name = $1)', db_name)
            await conn.execute('DELETE FROM drugs WHERE name = $1', db_name)
            deleted += 1
            
    print(f"Deleted {deleted} fake/missing-image drugs.")
    
    # Restore the image URLs for the valid ones
    for idx, row in df.iterrows():
        img = row['image_url']
        name = row['name']
        if name in valid_names:
            await conn.execute('UPDATE drugs SET image_url = $1 WHERE name = $2', str(img), str(name))
            
    print("Database cleaned and original 66 rows with valid images are restored!")
    await conn.close()

asyncio.run(clean_db())
