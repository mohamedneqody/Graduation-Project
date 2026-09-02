import httpx
from fastapi import BackgroundTasks
import json

async def trigger_n8n_workflow(payload: dict):
    """Simulates triggering an n8n webhook workflow."""
    print(f"Triggering n8n workflow with payload: {json.dumps(payload)}")
    # async with httpx.AsyncClient() as client:
    #     await client.post("http://n8n-url/webhook", json=payload)
    return {"status": "Workflow triggered"}

async def process_n8n_callback(payload: dict):
    """Processes incoming data from n8n."""
    print(f"Received n8n callback: {json.dumps(payload)}")
    return {"status": "Callback processed"}
