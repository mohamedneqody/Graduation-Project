import os
import psycopg2
import json

DB_URL = os.environ.get("EXPORT_DB_URL") or ""
OUTPUTS = [
    r'd:\Graduation Project\AI-COS-Pharmacy\supabase\seed.sql',
    r'D:\Graduation Project\اتصال محلي\supabase\seed.sql'
]

conn = psycopg2.connect(DB_URL, connect_timeout=15, sslmode='require')
cur = conn.cursor()

cur.execute('''
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name
''')
tables = [r[0] for r in cur.fetchall()]

output_lines = ["SET session_replication_role = 'replica';\n"]
total_rows = 0

for table in tables:
    cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' AND table_name = '{table}' ORDER BY ordinal_position")
    cols_info = cur.fetchall()
    columns = [r[0] for r in cols_info]
    col_types = {r[0]: r[1] for r in cols_info}
    
    cur.execute(f'SELECT * FROM "{table}"')
    rows = cur.fetchall()
    if not rows: continue
    
    output_lines.append(f'-- Table: {table}')
    output_lines.append(f'DELETE FROM "{table}";')
    cols_str = ', '.join([f'"{c}"' for c in columns])
    
    for row in rows:
        values = []
        for i, val in enumerate(row):
            col_name = columns[i]
            ctype = col_types.get(col_name, '')
            
            if val is None:
                values.append('NULL')
            elif isinstance(val, bool):
                values.append('TRUE' if val else 'FALSE')
            elif isinstance(val, (int, float)):
                values.append(str(val))
            elif ctype == 'ARRAY' and isinstance(val, list):
                if not val:
                    values.append("'{}'")
                else:
                    arr_vals = []
                    for v in val:
                        if v is None: arr_vals.append('NULL')
                        elif isinstance(v, (int, float)): arr_vals.append(str(v))
                        else: arr_vals.append("'" + str(v).replace("'", "''") + "'")
                    values.append(f"ARRAY[{', '.join(arr_vals)}]::text[]")
            elif isinstance(val, (dict, list)):
                escaped = json.dumps(val).replace("'", "''")
                values.append(f"'{escaped}'::jsonb")
            else:
                escaped = str(val).replace("'", "''")
                values.append(f"'{escaped}'")
                
        vals_str = ', '.join(values)
        output_lines.append(f'INSERT INTO "{table}" ({cols_str}) VALUES ({vals_str});')
        
    output_lines.append('')
    total_rows += len(rows)
    print(f'OK {table}: {len(rows)}')

output_lines.append("SET session_replication_role = 'origin';\n")
for out_path in OUTPUTS:
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    print(f"Saved: {out_path}")
    
print("Seed exported successfully with correct array syntax.")
