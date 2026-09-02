import asyncio
import httpx

async def test_ollama():
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "customer_name": "Target A",
            "drug_name": "trypsoxir 10 chew tabs",
            "discount_percentage": 15
        }
        print("Waiting for Ollama to generate a message (this might take up to 30 seconds)...")
        response = await client.post("http://127.0.0.1:8000/api/v1/agents/marketing/generate-campaign", json=payload)
        print("Status:", response.status_code)
        print("Response:", response.json())

if __name__ == "__main__":
    asyncio.run(test_ollama())
