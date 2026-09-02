import asyncio
import asyncpg
import os
import re
from dotenv import load_dotenv

load_dotenv('d:\\Graduation Project\\backend\\backend\\.env')
url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')

async def revert_images():
    conn = await asyncpg.connect(url)
    
    # Read the log files to find updated drugs
    logs = [
        r"C:\Users\zbook\.gemini\antigravity\brain\f060737c-82d1-4ac6-967a-2c159f8a03b1\.system_generated\tasks\task-11843.log",
        r"C:\Users\zbook\.gemini\antigravity\brain\f060737c-82d1-4ac6-967a-2c159f8a03b1\.system_generated\tasks\task-11896.log"
    ]
    
    drugs_to_revert = []
    
    for log_path in logs:
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Find lines like: Updated amaryl 2mg -> ... or Updated Amaryl 2mg to ...
                for line in content.split('\n'):
                    match = re.search(r'Updated (.+) (?:->|to) ', line)
                    if match:
                        drugs_to_revert.append(match.group(1).strip())
    
    drugs_to_revert = list(set(drugs_to_revert))
    print(f"Reverting {len(drugs_to_revert)} drugs: {drugs_to_revert}")
    
    for drug in drugs_to_revert:
        await conn.execute('UPDATE drugs SET image_url = NULL WHERE name ILIKE $1', f'%{drug}%')
        print(f"Reverted {drug}")
        
    await conn.close()

asyncio.run(revert_images())
