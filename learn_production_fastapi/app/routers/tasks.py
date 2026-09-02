"""
# مسؤوليته:
# إدارة الـ Endpoints الخاصة بمهام الخلفية (Background Tasks).
# يحتوي على أمثلة لمهام قصيرة يتم معالجتها بعد رد الـ API، ومهام طويلة تحتاج إلى تتبع الحالة.
#
# متى تستخدم BackgroundTasks المدمجة، ومتى تحتاج Celery؟
# - BackgroundTasks: 
#   تُستخدم للمهام البسيطة والقصيرة جداً (مثل إرسال إيميل ترحيب، أو تحديث عدّاد في الداتابيز).
#   وهي مرتبطة بـ Worker السيرفر الحالي، فلو السيرفر عمل Restart، المهمة هتضيع!
# 
# - Celery / Message Queue (RabbitMQ / Redis):
#   تُستخدم للمهام الثقيلة (معالجة فيديو، تقارير شهرية، سحب بيانات ضخمة)، 
#   لأنها بتشتغل في Process منفصل تماماً (Workers منفصلة)، ولو السيرفر الرئيسي وقع أو عملنا له
#   Restart، المهام بتفضل محفوظة في الـ Queue ولن تضيع.
"""
from typing import Dict
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, EmailStr
from app.services import tasks as task_service

router = APIRouter(prefix="/api/v1/tasks", tags=["Background Tasks"])

class EmailRequest(BaseModel):
    email: EmailStr

@router.post("/send-email-demo")
async def send_email_endpoint(request: EmailRequest, background_tasks: BackgroundTasks):
    """
    يستقبل إيميل ويرجع الرد فوراً، بينما يتم محاكاة إرسال الإيميل في الخلفية.
    المستخدم سيستلم الرد قبل انتهاء الـ 5 ثواني.
    """
    # نضيف المهمة إلى الخلفية
    background_tasks.add_task(task_service.simulate_send_email, request.email)
    
    # الرد يرجع فوراً بدون انتظار
    return {"message": "تم استلام الطلب، جاري إرسال الإيميل في الخلفية..."}

@router.post("/long-running-job")
async def start_long_job(background_tasks: BackgroundTasks):
    """
    مثال لمهمة طويلة جداً. نُرجع للعميل Task ID لكي يتابع الحالة لاحقاً.
    """
    task_id = task_service.create_task()
    background_tasks.add_task(task_service.simulate_long_job, task_id)
    
    return {"message": "Job started", "task_id": task_id}

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    نقطة استعلام (Polling) لمعرفة حالة المهمة.
    """
    status = task_service.get_task_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return {"task_id": task_id, "status": status}
