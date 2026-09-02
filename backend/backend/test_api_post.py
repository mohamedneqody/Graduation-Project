import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        # 1. Login to get token
        res = await client.post('http://127.0.0.1:8000/api/v1/auth/login', data={
            'username': 'mohameb.eslam460@gmail.com',
            'password': 'Password123!',
            'grant_type': 'password'
        })
        if res.status_code != 200:
            print("Login failed:", res.text)
            return
            
        token = res.json()['access_token']
        headers = {
            'Authorization': f'Bearer {token}',
            'X-Tenant-ID': '62712616-be1e-4129-986f-4131877e63b8',
            'Content-Type': 'application/json'
        }
        
        # 2. Add customer
        payload = {
            "full_name": "Test Customer",
            "email": "brand_new_email_999@gmail.com",
            "phone": "010704613313"
        }
        res2 = await client.post('http://127.0.0.1:8000/api/v1/customers/', json=payload, headers=headers)
        print("Add customer status:", res2.status_code)
        print("Response:", res2.text)

if __name__ == '__main__':
    asyncio.run(main())
