import sqlite3
conn = sqlite3.connect(r'C:\Users\zbook\.n8n\database.sqlite')
cursor = conn.cursor()
cursor.execute('SELECT id, name FROM workflow_entity')
workflows = cursor.fetchall()
print(f'Total Workflows: {len(workflows)}')
for w in workflows:
    print(f'- {w[1]}')
conn.close()
