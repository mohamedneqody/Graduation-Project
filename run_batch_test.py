
import asyncio
import httpx
import re
import json

async def run_tests():
    with open('D:/Graduation Project/????/?????_???????_?????_???????.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    questions = []
    for line in lines:
        line = line.strip()
        if re.match(r'^\d+\.', line):
            questions.append(line)
            
    print(f'Found {len(questions)} questions.')
    
    results = []
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        for q in questions[:5]: # testing first 5 to make sure it works
            print(f'Testing: {q}')
            try:
                res = await client.post('http://127.0.0.1:8000/api/v1/ai/chat', json={
                    'message': q,
                    'customer_name': 'Test User',
                    'session_id': 'test_batch_session'
                })
                data = res.json()
                results.append({'q': q, 'a': data.get('reply', 'Error'), 'source': data.get('llm_source')})
            except Exception as e:
                results.append({'q': q, 'a': str(e), 'source': 'Error'})
                
    with open('batch_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
if __name__ == '__main__':
    asyncio.run(run_tests())

