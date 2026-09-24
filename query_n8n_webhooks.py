import sqlite3, json
conn = sqlite3.connect(r'C:\Users\zbook\.n8n\database.sqlite')
cursor = conn.cursor()
cursor.execute('SELECT nodes FROM workflow_entity')
row = cursor.fetchone()
if row:
    nodes = json.loads(row[0])
    for n in nodes:
        print(f"- {n['name']} ({n['type']})")
conn.close()
