import asyncio
import asyncpg
import pandas as pd
import os
from dotenv import load_dotenv
import math

load_dotenv('d:\\Graduation Project\\backend\\backend\\.env')
url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')

async def restore():
    conn = await asyncpg.connect(url)
    
    # Read the original CSV
    df = pd.read_csv('C:\\Users\\zbook\\Downloads\\dawaagate_medicines_MERGED_FINAL (1).csv')
    
    count = 0
    for idx, row in df.iterrows():
        img = row['image_url']
        name = row['name_en']
        if pd.notna(img) and str(img).strip() != '' and str(img).strip() != 'null':
            # Restore this image in the DB
            await conn.execute('UPDATE drugs SET image_url = $1 WHERE name = $2', str(img), str(name))
            count += 1
            
    print(f"Restored {count} valid images from CSV!")
    await conn.close()

asyncio.run(restore())
