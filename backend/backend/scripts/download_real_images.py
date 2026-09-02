import csv
import re
import os
import urllib.request
import ssl

csv_path = r'C:\Users\zbook\Downloads\dawaagate_medicines_MERGED_FINAL (1).csv'
out_dir = r'd:\Graduation Project\stitch_ai_cos_pharmacy\ai-cos-frontend\public\drug-images'
os.makedirs(out_dir, exist_ok=True)

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row['name']
        img_url = row.get('image_url', '').strip()
        if not img_url:
            continue
            
        ext = os.path.splitext(img_url)[1]
        if not ext:
            ext = '.webp'
            
        slug = slugify(name)
        filename = f'{slug}{ext}'
        out_path = os.path.join(out_dir, filename)
        
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            print(f'Already downloaded: {filename}')
            continue
            
        try:
            req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as response, open(out_path, 'wb') as out_file:
                out_file.write(response.read())
            print(f'Downloaded: {filename}')
        except Exception as e:
            print(f'Failed to download {img_url}: {e}')
