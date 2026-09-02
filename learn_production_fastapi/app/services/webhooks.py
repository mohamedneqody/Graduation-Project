"""
# مسؤوليته:
# التواصل الفعلي مع n8n عبر HTTP وتتبع حالة مهام الـ Callbacks.
"""
import uuid
import httpx
from typing import Dict, Any

# In-Memory storage for callback tasks
CALLBACK_STORE: Dict[str, Dict[str, Any]] = {}

async def trigger_n8n_webhook(url: str, payload: Dict[str, Any]) -> dict | str:
    """يرسل طلب POST إلى n8n Webhook."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=5.0)
            # n8n عادة يرجع JSON، لكن أحياناً يرجع نص عادي
            if "application/json" in response.headers.get("Content-Type", ""):
                return response.json()
            return response.text
        except httpx.RequestError as e:
            return {"error": f"Failed to connect to n8n: {str(e)}"}

def create_task() -> str:
    task_id = str(uuid.uuid4())
    CALLBACK_STORE[task_id] = {"status": "processing", "result": None}
    return task_id

def update_task_status(task_id: str, status: str, result: Dict[str, Any]):
    if task_id in CALLBACK_STORE:
        CALLBACK_STORE[task_id]["status"] = status
        CALLBACK_STORE[task_id]["result"] = result
    else:
        # تسجيل دخول المهمة حتى لو لم تكن موجودة
        CALLBACK_STORE[task_id] = {"status": status, "result": result}

def get_task_status(task_id: str) -> Dict[str, Any]:
    return CALLBACK_STORE.get(task_id, {"error": "Task not found"})
