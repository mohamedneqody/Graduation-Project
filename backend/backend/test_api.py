import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        # Create a dummy image
        files = {'file': ('dummy.jpg', b'dummy content', 'image/jpeg')}
        response = await client.post('http://127.0.0.1:9202/api/analyze', files=files)
        print(response.status_code)
        print(response.text)

if __name__ == '__main__':
    asyncio.run(main())
