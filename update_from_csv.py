import pandas as pd
import asyncio
import asyncpg

async def run():
    df = pd.read_csv('final_images.csv')
    conn = await asyncpg.connect('postgresql://aicos_app.quhfheudhewxqmvxwjij:secure_aicos_app_pass_2026@aws-0-eu-central-1.pooler.supabase.com:5432/postgres')
    
    success = 0
    not_found = []
    
    for _, row in df.iterrows():
        name = str(row.iloc[0]).strip()
        url = str(row.iloc[1]).strip()
        
        # update by exact name (case-insensitive just in case)
        res = await conn.execute('UPDATE drugs SET image_url = $1 WHERE name ILIKE $2', url, name)
        if res == 'UPDATE 1':
            success += 1
        elif res == 'UPDATE 0':
            # Try to match by lowercase
            res2 = await conn.execute('UPDATE drugs SET image_url = $1 WHERE LOWER(name) = LOWER($2)', url, name)
            if res2 == 'UPDATE 1':
                success += 1
            else:
                not_found.append(name)
    
    print(f'Successfully updated {success} out of {len(df)} drugs.')
    if not_found:
        print('Could not find:', not_found)
        
    await conn.close()

asyncio.run(run())
