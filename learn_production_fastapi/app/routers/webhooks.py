"""
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
