import os
import re

base_path = r"d:\Graduation Project\learn_production_fastapi"

files = {
    "app/routers/enterprise.py": '''"""
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
''',

    "app/services/enterprise.py": '''"""
# مسؤوليته:
# تطبيق المنطق المعقد للـ Caching، والـ Queues، والـ Pagination بشكل نظيف.
# (Clean Architecture: لا يعرف شيئاً عن الـ Request أو الـ Router).
"""
import asyncio
import time
from typing import Tuple, Dict, Any, List

# --- 1. Caching Simulation ---
# في الإنتاج، يكون هذا اتصالاً بـ Redis
CACHE_STORE: Dict[str, Any] = {}

async def get_statistics_with_cache(use_cache: bool) -> Tuple[Dict, float, str]:
    start_time = time.perf_counter()
    cache_key = "global_stats"
    
    if use_cache and cache_key in CACHE_STORE:
        # Cache Hit (نجلبها من الذاكرة فوراً)
        result = CACHE_STORE[cache_key]
        source = "Cache (Redis/Memory)"
    else:
        # Cache Miss (نضطر لحسابها ببطء)
        await asyncio.sleep(2.0) # محاكاة عملية معقدة تأخذ ثانيتين
        result = {"total_users": 15000, "active_today": 4320, "revenue": 95000.50}
        
        # حفظها في الكاش للمرات القادمة
        CACHE_STORE[cache_key] = result
        source = "Database (Slow Computation)"
        
    end_time = time.perf_counter()
    return result, (end_time - start_time), source

# --- 3. Message Queue Simulation ---
# طابور رسائل يعمل في الذاكرة (يحاكي RabbitMQ أو Redis Queue)
TASK_QUEUE = asyncio.Queue()

async def add_task_to_queue(task_name: str):
    await TASK_QUEUE.put(task_name)

async def background_worker():
    """
    هذا الـ Worker يعمل في حلقة لا نهائية بالخلفية،
    يسحب المهام من الطابور وينفذها واحدة تلو الأخرى.
    """
    while True:
        task = await TASK_QUEUE.get()
        print(f"[Worker] Started processing task: {task}")
        await asyncio.sleep(3.0) # محاكاة معالجة المهمة
        print(f"[Worker] Finished processing task: {task}")
        TASK_QUEUE.task_done()

# --- 4. Pagination Simulation ---
# قاعدة بيانات وهمية كبيرة
FAKE_DB = [{"id": i, "name": f"User {i}"} for i in range(1, 10001)]

def get_paginated_data(limit: int, offset: int) -> Tuple[List[Dict], int]:
    total = len(FAKE_DB)
    # حماية من طلب حجم هائل
    if limit > 100:
        limit = 100
        
    data = FAKE_DB[offset : offset + limit]
    return data, total
'''
}

for rel_path, content in files.items():
    full_path = os.path.join(base_path, rel_path.replace("/", os.sep))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

# Update main.py to add slowapi, worker startup, and enterprise router
main_py_path = os.path.join(base_path, "app/main.py")
with open(main_py_path, "r", encoding="utf-8") as f:
    main_content = f.read()

# Prepare additions
slowapi_imports = '''
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.routers.enterprise import limiter
'''

startup_event = '''
import asyncio
from app.services.enterprise import background_worker

@app.on_event("startup")
async def startup_event():
    # تشغيل الـ Worker الخاص بالطابور (Queue) في الخلفية
    asyncio.create_task(background_worker())
'''

# Apply SlowAPI config and handlers
if "from slowapi" not in main_content:
    # Add imports near the top
    main_content = main_content.replace("from fastapi import FastAPI", "from fastapi import FastAPI" + slowapi_imports)
    
    # Add rate limiter state to app
    app_creation = "app = FastAPI(title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION)"
    app_config = app_creation + "\\napp.state.limiter = limiter\\napp.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)\\n"
    main_content = main_content.replace(app_creation, app_config)

# Apply Startup event
if '@app.on_event("startup")' not in main_content:
    main_content += startup_event

# Include enterprise router
if "from app.routers import products, demo_async, files, tasks, ai, webhooks" in main_content:
    if ", enterprise" not in main_content:
        main_content = main_content.replace(
            "from app.routers import products, demo_async, files, tasks, ai, webhooks",
            "from app.routers import products, demo_async, files, tasks, ai, webhooks, enterprise"
        )
        main_content += "\napp.include_router(enterprise.router)\n"

with open(main_py_path, "w", encoding="utf-8") as f:
    f.write(main_content)

print("Enterprise features configured.")
