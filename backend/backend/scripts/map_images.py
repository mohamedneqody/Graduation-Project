import pandas as pd
import asyncio
import asyncpg
import os
import uuid
from dotenv import load_dotenv

load_dotenv('d:\\Graduation Project\\backend\\backend\\.env')
url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')

async def main():
    csv_path = r'C:\Users\zbook\Downloads\dawaagate_medicines_MERGED_FINAL (1).csv'
    excel_path = r'D:\مشروع تخرج\medicines_image_links.xlsx'
    
    # Read Excel file
    try:
        df_excel = pd.read_excel(excel_path)
    except Exception as e:
        print("Failed to read Excel:", e)
        return

    name_col = next((c for c in df_excel.columns if 'name' in str(c).lower() or 'اسم' in str(c)), df_excel.columns[0])
    link_col = next((c for c in df_excel.columns if 'image' in str(c).lower() or 'url' in str(c).lower() or 'link' in str(c).lower() or 'صورة' in str(c) or 'رابط' in str(c)), df_excel.columns[1])
    
    # Create mapping dictionary
    mapping = dict(zip(df_excel[name_col], df_excel[link_col]))
    
    # Read CSV
    df_csv = pd.read_csv(csv_path)
    
    # Update missing image_url
    updated_count = 0
    drugs_to_insert = []
    
    for idx, row in df_csv.iterrows():
        img = row.get('image_url')
        name = row.get('name')
        
        # If image is missing
        if pd.isna(img) or str(img).strip() == '' or str(img).strip() == 'null':
            # Find matching in mapping (case-insensitive if possible)
            match = next((v for k, v in mapping.items() if str(k).strip().lower() == str(name).strip().lower()), None)
            
            if match:
                df_csv.at[idx, 'image_url'] = match
                updated_count += 1
                row_dict = row.to_dict()
                row_dict['image_url'] = match
                drugs_to_insert.append(row_dict)
                
    print(f"Mapped {updated_count} images from Excel to CSV.")
    
    # Save the updated CSV
    df_csv.to_csv(csv_path, index=False)
    print("Saved updated CSV.")
    
    # Now insert these drugs into the database!
    if drugs_to_insert:
        conn = await asyncpg.connect(url)
        inserted = 0
        for row in drugs_to_insert:
            # Check if it already exists
            exists = await conn.fetchval("SELECT 1 FROM drugs WHERE name = $1", row['name'])
            if not exists:
                drug_id = str(uuid.uuid4())
                await conn.execute('''
                    INSERT INTO drugs (drug_id, name, category, is_chronic, base_price, default_cycle_days, image_url)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                ''', 
                drug_id, 
                row['name'], 
                row.get('category'), 
                row.get('is_chronic') == True or str(row.get('is_chronic')).lower() == 'true',
                float(row.get('base_price', 0)),
                int(row.get('default_cycle_days', 30)),
                row['image_url'])
                inserted += 1
                
        print(f"Inserted {inserted} mapped drugs into the database.")
        await conn.close()

asyncio.run(main())
