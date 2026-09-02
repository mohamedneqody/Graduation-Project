import asyncio
import csv
import os
import re
import httpx
from dotenv import load_dotenv

load_dotenv()

async def process_csv():
    input_csv = r"C:\Users\zbook\Downloads\dawaagate_medicines_MERGED_FINAL.csv"
    output_csv = r"d:\Graduation Project\backend\backend\seed_data\final_drugs_sheet.csv"
    
    url = os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Missing Supabase credentials!")
        return

    storage_base_url = f"{url}/storage/v1"
    headers = {
        "Authorization": f"Bearer {key}",
        "apikey": key
    }
    
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
    print(f"Loaded {len(rows)} rows from {input_csv}")
    
    processed_rows = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, row in enumerate(rows):
            img_url = row.get('image_url', '').strip()
            new_img_url = img_url
            
            # Fix Feroglobin category
            if row.get('name', '').lower().strip() == 'feroglobin' or row.get('category') == 'فيتامينات - حديد':
                row['category'] = 'فيتامينات'

            if img_url and img_url.startswith('http') and 'supabase.co' not in img_url:
                en_name = row['name']
                safe_name = re.sub(r'[^a-zA-Z0-9-]', '-', en_name).strip('-').lower()
                safe_name = re.sub(r'-+', '-', safe_name)
                
                # Extract extension from URL
                ext = img_url.split('.')[-1]
                if len(ext) > 4 or '/' in ext:
                    ext = 'webp'
                    
                filename = f"{safe_name}.{ext}"
                public_url = f"{url}/storage/v1/object/public/drug-images/{filename}"
                
                print(f"[{i+1}/{len(rows)}] Downloading {img_url} ...")
                try:
                    img_resp = await client.get(img_url, headers={"User-Agent": "Mozilla/5.0"})
                    if img_resp.status_code == 200:
                        upload_resp = await client.post(
                            f"{storage_base_url}/object/drug-images/{filename}",
                            headers={**headers, "Content-Type": f"image/{ext}"},
                            content=img_resp.content
                        )
                        new_img_url = public_url
                        print(f" -> Uploaded to {public_url}")
                    else:
                        print(f" -> Failed to download: {img_resp.status_code}")
                except Exception as e:
                    print(f" -> Error downloading: {e}")
                
                await asyncio.sleep(0.5)
            
            # Update row
            row['image_url'] = new_img_url
            processed_rows.append(row)
            
    # Save to final_drugs_sheet.csv
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['name', 'category', 'is_chronic', 'base_price', 'default_cycle_days', 'image_url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(processed_rows)
        
    print(f"Finished processing {len(processed_rows)} rows. Saved to {output_csv}")

if __name__ == "__main__":
    asyncio.run(process_csv())
