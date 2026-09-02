import asyncio
import os
import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv
import difflib

async def main():
    load_dotenv(r'D:\Graduation Project\backend\backend\.env')
    engine = create_async_engine(os.environ.get('DATABASE_URL'))
    
    excel_path = r'C:\Users\zbook\Downloads\medicines_ALL_49_to_fill.xlsx'
    print(f"Reading {excel_path}...")
    df = pd.read_excel(excel_path)
    
    col_name = df.columns[0] # "اسم الصنف"
    col_url = df.columns[1] # "رابط الصورة..."
    
    async with engine.begin() as conn:
        res = await conn.execute(text('SELECT drug_id, name FROM drugs'))
        db_drugs = res.fetchall()
        
        db_names = [row.name for row in db_drugs]
        db_map = {row.name.lower(): row.drug_id for row in db_drugs}
        
        updated_count = 0
        for index, row in df.iterrows():
            excel_name = str(row[col_name]).strip()
            excel_url = str(row[col_url]).strip()
            
            if pd.isna(excel_name) or excel_name == 'nan':
                continue
                
            # Clean up excel name a bit for matching (remove text in parentheses)
            clean_excel_name = excel_name.split('(')[0].strip().lower()
            
            best_match = None
            best_score = 0
            
            # Substring match first
            for db_name in db_names:
                if db_name.lower() in clean_excel_name or clean_excel_name in db_name.lower():
                    best_match = db_name
                    best_score = 1.0
                    break
            
            # If no substring match, use difflib
            if not best_match:
                matches = difflib.get_close_matches(clean_excel_name, [n.lower() for n in db_names], n=1, cutoff=0.5)
                if matches:
                    best_match = next((n for n in db_names if n.lower() == matches[0]), None)
            
            if best_match:
                drug_id = db_map[best_match.lower()]
                await conn.execute(
                    text("UPDATE drugs SET image_url = :url WHERE drug_id = :id"),
                    {"url": excel_url, "id": drug_id}
                )
                print(f"Mapped: '{excel_name}' -> '{best_match}'")
                updated_count += 1
            else:
                print(f"NO MATCH FOUND for '{excel_name}'")
                
        print(f"\nTotal updated: {updated_count} out of {len(df)}")

if __name__ == "__main__":
    asyncio.run(main())
