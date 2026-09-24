import psycopg2
import os

DB_URL = os.environ.get("EXPORT_DB_URL") or ""
OUTPUT = r"d:\Graduation Project\AI-COS-Pharmacy\supabase\migrations\20260101000000_initial_schema.sql"

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

conn = psycopg2.connect(DB_URL, connect_timeout=15, sslmode='require')
cur = conn.cursor()

lines = []
lines.append("-- Auto-generated schema migration from Supabase Cloud")
lines.append("-- Project: Graduation Project (quhfheudhewxqmvxwjij)\n")

# 1. ENUM types
cur.execute("""
    SELECT t.typname, array_agg(e.enumlabel ORDER BY e.enumsortorder) as values
    FROM pg_type t
    JOIN pg_enum e ON t.oid = e.enumtypid
    JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'public'
    GROUP BY t.typname
""")
enums = cur.fetchall()
if enums:
    lines.append("-- ENUM Types")
    for name, values in enums:
        vals = ", ".join([f"'{v}'" for v in values])
        lines.append(f"CREATE TYPE IF NOT EXISTS \"{name}\" AS ENUM ({vals});")
    lines.append("")

# 2. Tables with columns
cur.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name
""")
tables = [r[0] for r in cur.fetchall()]
print(f"Found {len(tables)} tables")

for table in tables:
    cur.execute(f"""
        SELECT
            c.column_name,
            c.data_type,
            c.udt_name,
            c.character_maximum_length,
            c.numeric_precision,
            c.numeric_scale,
            c.is_nullable,
            c.column_default,
            c.is_identity,
            c.identity_generation
        FROM information_schema.columns c
        WHERE c.table_schema = 'public' AND c.table_name = '{table}'
        ORDER BY c.ordinal_position
    """)
    cols = cur.fetchall()

    col_defs = []
    for col in cols:
        col_name, data_type, udt_name, char_max, num_prec, num_scale, nullable, default, is_identity, identity_gen = col
        
        # Determine type
        if data_type == 'USER-DEFINED':
            col_type = f'"{udt_name}"'
        elif data_type == 'character varying':
            col_type = f'VARCHAR({char_max})' if char_max else 'TEXT'
        elif data_type == 'character':
            col_type = f'CHAR({char_max})' if char_max else 'CHAR'
        elif data_type == 'numeric' and num_prec:
            col_type = f'NUMERIC({num_prec},{num_scale or 0})'
        elif data_type == 'ARRAY':
            col_type = f'{udt_name.lstrip("_")}[]'
        else:
            col_type = data_type.upper()
        
        col_def = f'    "{col_name}" {col_type}'
        
        if is_identity == 'YES':
            col_def += f' GENERATED {identity_gen} AS IDENTITY'
        elif default:
            col_def += f' DEFAULT {default}'
        
        if nullable == 'NO':
            col_def += ' NOT NULL'
        
        col_defs.append(col_def)

    lines.append(f'CREATE TABLE IF NOT EXISTS "{table}" (')
    lines.append(',\n'.join(col_defs))
    lines.append(');')
    lines.append('')
    print(f"  OK {table}: {len(cols)} columns")

# 3. Primary Keys
cur.execute("""
    SELECT tc.table_name, tc.constraint_name, kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type = 'PRIMARY KEY'
    AND tc.table_schema = 'public'
    ORDER BY tc.table_name, kcu.ordinal_position
""")
pks_raw = cur.fetchall()
pks = {}
for table, constraint, col in pks_raw:
    pks.setdefault(table, {'constraint': constraint, 'cols': []})['cols'].append(col)

if pks:
    lines.append("-- Primary Keys")
    for table, info in pks.items():
        cols = ', '.join([f'"{c}"' for c in info['cols']])
        lines.append(f'ALTER TABLE "{table}" ADD CONSTRAINT "{info["constraint"]}" PRIMARY KEY ({cols});')
    lines.append("")

# 4. Foreign Keys
cur.execute("""
    SELECT
        tc.table_name, tc.constraint_name,
        kcu.column_name,
        ccu.table_name AS foreign_table,
        ccu.column_name AS foreign_column,
        rc.delete_rule
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
    JOIN information_schema.referential_constraints rc
        ON tc.constraint_name = rc.constraint_name AND tc.table_schema = rc.constraint_schema
    JOIN information_schema.constraint_column_usage ccu
        ON rc.unique_constraint_name = ccu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
    ORDER BY tc.table_name
""")
fks = cur.fetchall()
if fks:
    lines.append("-- Foreign Keys")
    for table, constraint, col, ftable, fcol, del_rule in fks:
        on_del = f" ON DELETE {del_rule}" if del_rule != 'NO ACTION' else ""
        lines.append(f'ALTER TABLE "{table}" ADD CONSTRAINT "{constraint}" FOREIGN KEY ("{col}") REFERENCES "{ftable}"("{fcol}"){on_del};')
    lines.append("")

# 5. Indexes
cur.execute("""
    SELECT indexname, tablename, indexdef
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND indexname NOT LIKE '%_pkey'
    ORDER BY tablename, indexname
""")
indexes = cur.fetchall()
if indexes:
    lines.append("-- Indexes")
    for idx_name, tbl, idx_def in indexes:
        lines.append(f"{idx_def};")
    lines.append("")

# 6. RLS Policies
cur.execute("""
    SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
    FROM pg_policies
    WHERE schemaname = 'public'
    ORDER BY tablename, policyname
""")
policies = cur.fetchall()
if policies:
    lines.append("-- Enable RLS")
    rls_tables = set()
    for schema, table, policy, permissive, roles, cmd, qual, with_check in policies:
        if table not in rls_tables:
            lines.append(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;')
            rls_tables.add(table)
    lines.append("")
    lines.append("-- RLS Policies")
    for schema, table, policy, permissive, roles, cmd, qual, with_check in policies:
        perm = "PERMISSIVE" if permissive == 'PERMISSIVE' else "RESTRICTIVE"
        roles_str = ', '.join(roles) if roles else 'public'
        pol_line = f'CREATE POLICY "{policy}" ON "{table}" AS {perm} FOR {cmd} TO {roles_str}'
        if qual:
            pol_line += f' USING ({qual})'
        if with_check:
            pol_line += f' WITH CHECK ({with_check})'
        lines.append(pol_line + ';')
    lines.append("")

conn.close()

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"\nDone! Schema saved to:")
print(OUTPUT)
