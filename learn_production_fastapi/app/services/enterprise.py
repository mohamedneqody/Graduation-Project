"""
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
