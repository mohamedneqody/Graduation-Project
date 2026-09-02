import pandas as pd

excel_path = r'C:\Users\zbook\Downloads\medicines_ALL_49_to_fill.xlsx'
csv_path = r'D:\Graduation Project\backend\backend\seed_data\final_drugs_sheet.csv'

df_excel = pd.read_excel(excel_path)
df_csv = pd.read_csv(csv_path)

csv_names = set(df_csv['name'].astype(str).str.strip().str.lower())

unmatched = []
for idx, row in df_excel.iterrows():
    name = str(row['اسم الصنف']).strip()
    url = str(row['رابط الصورة (مباشر ومتأكد إنه شغّال)']).strip()
    if pd.notna(url) and url != 'nan':
        if name.lower() not in csv_names:
            unmatched.append(name)

with open('unmatched_names.txt', 'w', encoding='utf-8') as f:
    for n in unmatched:
        f.write(n + '\n')
