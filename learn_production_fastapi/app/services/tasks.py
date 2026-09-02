"""
# مسؤوليته:
# معالجة المهام الخلفية وتتبع حالة المهام الطويلة في الذاكرة (Memory).
"""
import uuid
import asyncio

# قاموس في الذاكرة (In-Memory Dict) لتتبع حالة المهام البسيطة
# ملاحظة: في بيئة الإنتاج، نستخدم Redis أو Database لحفظ الحالة، وليس الذاكرة.
JOBS_STORE: dict[str, str] = {}

async def simulate_send_email(email: str):
    """
    محاكاة لعملية بطيئة مثل إرسال إيميل.
    """
    print(f"[{email}] Start sending email...")
    await asyncio.sleep(5)  # محاكاة تأخير لمدة 5 ثواني
    print(f"[{email}] Email successfully sent!")

def create_task() -> str:
    """يُنشئ Task ID جديد ويحفظ حالته كـ 'pending'"""
    task_id = str(uuid.uuid4())
    JOBS_STORE[task_id] = "pending"
    return task_id

async def simulate_long_job(task_id: str):
    """
    محاكاة لعملية معالجة طويلة جداً (15 ثانية).
    تُحدث الحالة في القاموس عند الانتهاء.
    """
    print(f"[Task {task_id}] Job started...")
    await asyncio.sleep(15)
    JOBS_STORE[task_id] = "completed"
    print(f"[Task {task_id}] Job completed!")

def get_task_status(task_id: str) -> str | None:
    """يعيد حالة المهمة، أو None إذا لم تكن موجودة"""
    return JOBS_STORE.get(task_id)
