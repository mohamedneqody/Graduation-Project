import asyncio
import os
import httpx
from dotenv import load_dotenv

async def main():
    load_dotenv('D:/Graduation Project/stitch_ai_cos_pharmacy/ai-cos-frontend/.env.local')
    url = os.environ.get('NEXT_PUBLIC_SUPABASE_URL')
    anon_key = os.environ.get('NEXT_PUBLIC_SUPABASE_ANON_KEY')
    
    headers = {
        'apikey': anon_key,
        'Authorization': f'Bearer {anon_key}'
    }
    
    async with httpx.AsyncClient() as client:
        # Request from PostgREST API
        res = await client.get(f"{url}/rest/v1/customers?select=email,full_name", headers=headers)
        if res.status_code == 200:
            print("Customers via REST API:")
            for c in res.json():
                print(c)
        else:
            print("Error:", res.status_code, res.text)

if __name__ == '__main__':
    asyncio.run(main())
