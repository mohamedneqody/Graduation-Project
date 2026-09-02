
import asyncio
import httpx

async def main():
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000') as client:
        # Create a dummy image file
        files = {'file': ('test.jpg', b'dummy image data', 'image/jpeg')}
        
        # We need to simulate auth or bypass it? The endpoint uses get_current_user. 
        # I need a valid JWT or to bypass it.
        pass

if __name__ == '__main__':
    asyncio.run(main())

