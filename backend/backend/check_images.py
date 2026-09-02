import asyncio, sys, os, re
sys.stdout.reconfigure(encoding='utf-8')
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.models.drug import Drug

folder = r'D:\Graduation Project\stitch_ai_cos_pharmacy\واجهات_Premium_V2'

async def check_images():
    async with AsyncSessionLocal() as s:
        result = await s.execute(select(Drug.name, Drug.image_url))
        db_drugs = result.fetchall()
        db_map = {d.name: d.image_url for d in db_drugs if d.image_url}

    print('--- Database Images ---')
    for name, img in db_map.items():
        print(f'{name}: {img}')
    
    print('\n--- HTML Images ---')
    img_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']')
    
    for fname in os.listdir(folder):
        if not fname.endswith('.html'): continue
        path = os.path.join(folder, fname)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = img_pattern.findall(content)
            if matches:
                print(f'\n{fname}:')
                for m in set(matches):
                    print(f'  {m}')

asyncio.run(check_images())
