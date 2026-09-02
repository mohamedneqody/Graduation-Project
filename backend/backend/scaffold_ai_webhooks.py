import os

base_path = r"d:\Graduation Project\backend\backend\app\domains\ai"

files = {
    "__init__.py": "",
    "schemas.py": '''from pydantic import BaseModel

class AIChatRequest(BaseModel):
    message: str

class AIChatResponse(BaseModel):
    reply: str
''',
    "service.py": '''import httpx
from app.core.config import settings

async def generate_ai_response(message: str) -> str:
    """Mock implementation for AI response or simple HTTPX call to an LLM provider."""
    # In a real scenario, you'd use httpx to call Gemini or OpenAI API
    # async with httpx.AsyncClient() as client:
    #     response = await client.post(...)
    
    return f"AI received your message: {message}. This is a mock response."
''',
    "router.py": '''from fastapi import APIRouter
from . import schemas, service

router = APIRouter()

@router.post("/chat", response_model=schemas.AIChatResponse)
async def chat_with_ai(request: schemas.AIChatRequest):
    """
    Endpoint to communicate with external AI API (e.g., Gemini).
    """
    reply = await service.generate_ai_response(request.message)
    return {"reply": reply}
'''
}

for name, content in files.items():
    with open(os.path.join(base_path, name), "w", encoding="utf-8") as f:
        f.write(content)

base_path_webhooks = r"d:\Graduation Project\backend\backend\app\domains\webhooks"

files_webhooks = {
    "__init__.py": "",
    "schemas.py": '''from pydantic import BaseModel
from typing import Dict, Any

class WebhookPayload(BaseModel):
    payload: Dict[str, Any]
''',
    "service.py": '''import httpx
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
''',
    "router.py": '''from fastapi import APIRouter
from typing import Dict, Any
from . import schemas, service

router = APIRouter()

@router.post("/trigger", status_code=202)
async def trigger_workflow(payload: schemas.WebhookPayload):
    """
    Trigger an n8n workflow from our FastAPI backend.
    """
    return await service.trigger_n8n_workflow(payload.payload)

@router.post("/incoming")
async def incoming_webhook(payload: Dict[str, Any]):
    """
    Receive incoming HTTP requests from n8n.
    """
    return await service.process_n8n_callback(payload)
'''
}

for name, content in files_webhooks.items():
    with open(os.path.join(base_path_webhooks, name), "w", encoding="utf-8") as f:
        f.write(content)
