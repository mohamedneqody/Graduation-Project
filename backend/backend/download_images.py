import asyncio
import asyncpg
import aiohttp
import os
import ssl

DB_URL = 'postgresql://aicos_app.quhfheudhewxqmvxwjij:secure_aicos_app_pass_2026@aws-0-eu-central-1.pooler.supabase.com:5432/postgres'
TENANT_ID = '62712616-be1e-4129-986f-4131877e63b8'

async def download_image(session, url, filepath):
    if os.path.exists(filepath):
        return True
    try:
        async with session.get(url, timeout=15) as response:
            if response.status == 200:
                content = await response.read()
                with open(filepath, 'wb') as f:
                    f.write(content)
                return True
            print(f"Failed to download {url}, status: {response.status}")
            return False
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

async def main():
    target_dir = 'd:/Graduation Project/stitch_ai_cos_pharmacy/ai-cos-frontend/public/medicines'
    os.makedirs(target_dir, exist_ok=True)
    
    conn = await asyncpg.connect(DB_URL)
    # Set context to satisfy RLS
    await conn.execute("SELECT set_config('app.current_tenant_id', $1, false)", TENANT_ID)
    
    drugs = await conn.fetch("SELECT drug_id, name, image_url FROM drugs WHERE image_url LIKE 'http%'")
    print(f"Found {len(drugs)} drugs with external images")
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        for drug in drugs:
            url = drug['image_url']
            ext = url.split('.')[-1]
            if len(ext) > 4 or '?' in ext:
                ext = 'png'
            filename = f"{drug['drug_id']}.{ext}"
            filepath = os.path.join(target_dir, filename)
            local_url = f"/medicines/{filename}"
            
            print(f"Downloading {url} to {filename}...")
            success = await download_image(session, url, filepath)
            
            if success:
                # Update DB
                await conn.execute("UPDATE drugs SET image_url = $1 WHERE drug_id = $2", local_url, drug['drug_id'])
                print(f"Updated drug {drug['name']} -> {local_url}")
                
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
