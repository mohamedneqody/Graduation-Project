"""
# مسؤوليته:
# إدارة الـ Endpoints الخاصة بالميزات المتقدمة للإنتاج (Enterprise Features)
# يشمل: Caching, Rate Limiting, Message Queues, Pagination, Security.
"""
from fastapi import APIRouter, Request, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.services import enterprise as enterprise_service
from app.database.session import get_db

# إعداد Rate Limiter
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/v1/enterprise", tags=["Enterprise Features"])

# 1. Caching
@router.get("/statistics")
async def get_complex_statistics(use_cache: bool = True):
    """
    يحاكي عملية حسابية معقدة. يوضح الفرق في السرعة بين Cache Miss و Cache Hit.
    """
    result, time_taken, source = await enterprise_service.get_statistics_with_cache(use_cache)
    return {
        "data": result,
        "time_taken_seconds": round(time_taken, 4),
        "data_source": source
    }

# 2. Rate Limiting
@router.get("/rate-limited")
@limiter.limit("5/minute")
async def rate_limited_endpoint(request: Request):
    """
    مسموح بـ 5 طلبات فقط في الدقيقة لكل IP.
    """
    return {"message": "You successfully accessed the rate-limited endpoint!"}

# 3. Message Queue (Background Worker)
@router.post("/queue-task")
async def enqueue_task(task_name: str):
    """
    يضع المهمة في الطابور (Queue) ليعالجها الـ Worker في الخلفية بشكل منفصل تماماً عن هذا الـ Request.
    """
    await enterprise_service.add_task_to_queue(task_name)
    return {"message": f"Task '{task_name}' added to queue for background processing."}

# 4. Pagination
@router.get("/users")
async def get_paginated_users(limit: int = 10, offset: int = 0):
    """
    يجلب البيانات بنظام الصفحات (Pagination) بدلاً من إرجاع ملايين السجلات دفعة واحدة.
    """
    users, total = enterprise_service.get_paginated_data(limit, offset)
    return {
        "total_records": total,
        "limit": limit,
        "offset": offset,
        "data": users
    }

# 5. Security (SQL Injection)
@router.get("/security/vulnerable")
def vulnerable_sql_injection(username: str, db: Session = Depends(get_db)):
    """
    [تحذير]: هذا الكود خطير جداً! يوضح كيف يحدث الـ SQL Injection إذا دمجت النصوص بـ f-string.
    مثال لاختراقه: مرر `admin' OR '1'='1`
    """
    # هذا استعلام مباشر يخرق الـ Clean Architecture للاستعراض فقط
    try:
        query = f"SELECT * FROM users WHERE username = '{username}'"
        # db.execute(query) # معلق لحمايتك
        return {"vulnerable_query_executed": query, "warning": "DO NOT DO THIS"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/security/safe")
def safe_sql_query(username: str, db: Session = Depends(get_db)):
    """
    الكود الآمن! يستخدم الـ Parameterized Queries (التي يستخدمها SQLAlchemy تلقائياً).
    هنا الـ Database Driver يتعامل مع `username` كـ (نص) وليس كأمر تنفيذي.
    """
    try:
        from sqlalchemy import text
        # Parameterized query - SAFE
        query = text("SELECT * FROM users WHERE username = :username")
        # db.execute(query, {"username": username}) # معلق لأنه لا يوجد جدول حقيقي
        return {"safe_query_executed": "SELECT * FROM users WHERE username = :username", "status": "SAFE"}
    except Exception as e:
        return {"error": str(e)}
