import csv
import os

csv_path = os.path.join('seed_data', 'final_drugs_sheet.csv')
out_path = 'p11_seed_drugs.sql'

with open(csv_path, mode='r', encoding='utf-8-sig') as f, open(out_path, mode='w', encoding='utf-8') as out:
    reader = csv.DictReader(f)
    out.write('-- ============================================================\n')
    out.write('-- P11 Seed Drugs — AI-COS Pharmacy\n')
    out.write('-- Run this SQL in: Supabase Dashboard -> SQL Editor\n')
    out.write('-- This restores the 114 deleted drugs.\n')
    out.write('-- ============================================================\n\n')
    out.write('TRUNCATE TABLE public.drugs CASCADE;\n\n')
    
    for row in reader:
        is_chronic = 'true' if str(row['is_chronic']).lower().strip() == 'true' else 'false'
        bp = float(row['base_price'])
        dcd = int(row['default_cycle_days'])
        img = row['image_url'] if row['image_url'] else 'null'
        if img != 'null':
            img = f"'{img}'"
            
        name = row['name'].replace("'", "''")
        cat = row['category'].replace("'", "''")
        
        out.write(f"INSERT INTO public.drugs (drug_id, name, category, is_chronic, base_price, default_cycle_days, image_url) VALUES (gen_random_uuid(), '{name}', '{cat}', {is_chronic}, {bp}, {dcd}, {img});\n")
    
    out.write('\n-- Done!\n')

print('SQL file generated!')
