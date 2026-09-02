import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        # Assuming admin token or we bypass token?
        # The endpoint requires admin role.
        # Wait, if we don't have token, we'll get "Not authenticated".
        pass
    print("Test ready")

if __name__ == "__main__":
    asyncio.run(main())
