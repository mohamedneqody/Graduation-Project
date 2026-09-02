import asyncio
import httpx
import os
from dotenv import load_dotenv

async def main():
    load_dotenv('D:/Graduation Project/backend/backend/.env', override=True)
    url = os.environ.get('NEXT_PUBLIC_SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    
    if not url or not key:
        print("Missing SUPABASE config in backend/.env, trying frontend/.env.local...")
        load_dotenv('D:/Graduation Project/stitch_ai_cos_pharmacy/ai-cos-frontend/.env.local', override=True)
        url = os.environ.get('NEXT_PUBLIC_SUPABASE_URL')
        key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
        
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{url}/rest/v1/customers?select=email", 
            headers={'apikey': key, 'Authorization': f'Bearer {key}'}
        )
        print("All emails:", res.json())

if __name__ == '__main__':
    asyncio.run(main())
