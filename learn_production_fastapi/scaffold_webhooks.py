import os

base_path = r"d:\Graduation Project\learn_production_fastapi"

files = {
    "app/routers/webhooks.py": '''"""
# مسؤوليته:
# إدارة الـ Webhooks والاتصال بأنظمة الأتمتة الخارجية مثل n8n.
"""
from typing import Dict, Any
from fastapi import APIRouter, Request, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from app.services import webhooks as webhook_service
from app.services import files as file_service

router = APIRouter(prefix="/api/v1/webhooks", tags=["n8n Integration"])

class TriggerRequest(BaseModel):
    workflow_id: str
    payload: Dict[str, Any]

class CallbackPayload(BaseModel):
    task_id: str
    status: str
    result_data: Dict[str, Any]

# 1. Incoming Webhook (من n8n إلى FastAPI)
@router.post("/n8n/incoming")
async def receive_from_n8n(request: Request):
    """
    يستقبل بيانات (JSON) من n8n.
    في n8n: 
    - أضف عقدة (HTTP Request Node).
    - Method: POST
    - URL: http://host.docker.internal:8000/api/v1/webhooks/n8n/incoming 
      (استخدم host.docker.internal لو n8n في دوكر والـ API على الجهاز المحلي).
    - Send Body: مفعل (JSON).
    """
    data = await request.json()
    print(f"[Webhook Received] Data from n8n: {data}")
    return {"message": "Webhook received successfully", "received_keys": list(data.keys())}

# 2. Trigger n8n Workflow (من FastAPI إلى n8n)
@router.post("/trigger-workflow")
async def trigger_n8n(request: TriggerRequest):
    """
    يستدعي Webhook خاص بـ n8n لبدء Workflow.
    """
    # في n8n يجب أن يكون لديك Webhook Node يستمع لهذا الرابط
    n8n_webhook_url = f"http://localhost:5678/webhook/{request.workflow_id}"
    
    response_data = await webhook_service.trigger_n8n_webhook(n8n_webhook_url, request.payload)
    return {"message": "n8n workflow triggered", "n8n_response": response_data}

# 3. Callback (من n8n إلى FastAPI بعد مهمة طويلة)
@router.post("/n8n/callback")
async def n8n_callback(payload: CallbackPayload):
    """
    يستقبل نتيجة من n8n بعد انتهاء عملية طويلة.
    """
    webhook_service.update_task_status(payload.task_id, payload.status, payload.result_data)
    return {"message": "Task status updated via callback"}

@router.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    return webhook_service.get_task_status(task_id)

# 4. File Processing Trigger (رفع ملف وإرساله لـ n8n)
@router.post("/process-file")
async def upload_and_process_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    يستقبل ملفاً، يحفظه محلياً، ثم يرسل المسار إلى n8n للمعالجة في الخلفية.
    """
    # حفظ الملف باستخدام الـ Service الخاصة بالملفات (التي برمجناها مسبقاً)
    filename = await file_service.save_file(file, "n8n_processing")
    file_path = file_service.get_file_path(filename)
    
    task_id = webhook_service.create_task()
    
    # إبلاغ n8n بوجود ملف يحتاج معالجة (في الخلفية لكي لا ينتظر المستخدم)
    # نرسل له الـ task_id لكي يعيده لنا في الـ Callback
    payload = {
        "task_id": task_id,
        "file_path": file_path,
        "action": "extract_text"
    }
    
    n8n_webhook_url = "http://localhost:5678/webhook/file-processor"
    background_tasks.add_task(webhook_service.trigger_n8n_webhook, n8n_webhook_url, payload)
    
    return {
        "message": "File received. n8n is processing it in the background.",
        "task_id": task_id
    }
''',

    "app/services/webhooks.py": '''"""
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
'''
}

for rel_path, content in files.items():
    full_path = os.path.join(base_path, rel_path.replace("/", os.sep))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

# تسجيل الـ Router في main.py
main_py_path = os.path.join(base_path, "app/main.py")
with open(main_py_path, "r", encoding="utf-8") as f:
    main_content = f.read()

if "from app.routers import products, demo_async, files, tasks, ai, webhooks" not in main_content:
    main_content = main_content.replace(
        "from app.routers import products, demo_async, files, tasks, ai",
        "from app.routers import products, demo_async, files, tasks, ai, webhooks"
    )
    if "app.include_router(webhooks.router)" not in main_content:
        main_content += "\napp.include_router(webhooks.router)\n"
    
    with open(main_py_path, "w", encoding="utf-8") as f:
        f.write(main_content)

print("Webhooks endpoints configured.")
