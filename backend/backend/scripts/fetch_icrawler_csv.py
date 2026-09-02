import pandas as pd
from pathlib import Path
from icrawler.builtin import BingImageCrawler
import os

CSV_FILE = r"C:\Users\zbook\Downloads\dawaagate_medicines_MERGED_FINAL (1).csv"
FRONTEND_IMAGES_DIR = Path(r"d:\Graduation Project\stitch_ai_cos_pharmacy\ai-cos-frontend\public\drug-images")

def fetch_images():
    df = pd.read_csv(CSV_FILE)
    missing = []
    for _, row in df.iterrows():
        url = row.get('image_url')
        if pd.isna(url) or url == 'null' or url == '':
            missing.append(row)
        else:
            filename = str(url).split('/')[-1]
            filepath = FRONTEND_IMAGES_DIR / filename
            if not filepath.exists():
                missing.append(row)

    print(f"Found {len(missing)} missing drugs.")
    
    for row in missing:
        query = f"{row['name']} medicine box egypt"
        print(f"Searching for: {query}")
        
        crawler = BingImageCrawler(storage={'root_dir': str(FRONTEND_IMAGES_DIR)})
        before = set(os.listdir(FRONTEND_IMAGES_DIR))
        crawler.crawl(keyword=query, max_num=1)
        after = set(os.listdir(FRONTEND_IMAGES_DIR))
        new_files = after - before
        
        if new_files:
            new_file = new_files.pop()
            ext = new_file.split('.')[-1]
            slug = row['name'].lower().replace(' ', '-').replace('/', '-').replace('(', '').replace(')', '')
            new_name = f"{slug}.{ext}"
            
            old_path = FRONTEND_IMAGES_DIR / new_file
            new_path = FRONTEND_IMAGES_DIR / new_name
            
            if new_path.exists():
                new_path.unlink()
                
            old_path.rename(new_path)
            print(f" -> Saved {new_name}")
        else:
            print(f" -> Failed to find image for {row['name']}")

if __name__ == "__main__":
    fetch_images()
