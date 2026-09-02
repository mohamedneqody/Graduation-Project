import asyncio
import httpx
from uuid import UUID

async def main():
    payload = {
        "full_name": "Test Customer",
        "email": "test8888888888@gmail.com",
        "phone": "010704613313"
    }
    headers = {
        "X-Tenant-ID": "62712616-be1e-4129-986f-4131877e63b8",
        # Send a fake JWT just to see if it bypasses or what
        # Actually I can't bypass unless I mock the dependency.
    }
    
    # I will patch router.py temporarily to skip auth!
    
if __name__ == '__main__':
    asyncio.run(main())
