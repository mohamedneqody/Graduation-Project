"""
# مسؤوليته:
# توضيح الفرق بين العمليات المتزامنة (Sync) وغير المتزامنة (Async) في FastAPI.
# يحتوي على أمثلة لمحاكاة وقت الانتظار (Sleep)، طلبات الشبكة (HTTP)، وقواعد البيانات (DB).
"""
import time
import asyncio
import sqlite3
import aiosqlite
import httpx
from fastapi import APIRouter

router = APIRouter(tags=["Async Demo"])

# --- 1. أمثلة الانتظار (Sleep) ---

@router.get("/demo/sync-sleep")
def sync_sleep():
    """
    مثال على Endpoint متزامن (Sync).
    FastAPI ذكي كفاية، لما بيشوف `def` عادي، بيشغل الدالة دي في Thread Pool منفصل
    عشان `time.sleep` (اللي بتوقف الـ Thread بالكامل) ما توقفش السيرفر كله.
    """
    time.sleep(2)  # عملية بطيئة توقف الـ Thread الحالي
    return {"message": "Sync sleep finished", "duration": 2}

@router.get("/demo/async-sleep")
async def async_sleep():
    """
    مثال على Endpoint غير متزامن (Async).
    لما السيرفر يوصل لـ `await`، بيسيب الـ Request ده يرتاح ويروح يخدم طلب تاني
    لحد ما الـ 2 ثانية يخلصوا. ده بيوفر الموارد جداً (لأنه بيشتغل على Thread واحد للـ Event Loop).
    """
    await asyncio.sleep(2)  # عملية بطيئة بتسمح للسيرفر يشتغل في حاجة تانية
    return {"message": "Async sleep finished", "duration": 2}


# --- 2. أمثلة الشبكة (HTTP) ---

@router.get("/demo/async-http")
async def fetch_github_async():
    """
    مثال على طلب HTTP خارجي بشكل Async باستخدام مكتبة `httpx`.
    
    تحذير: لو استخدمنا مكتبة `requests` (وهي مكتبة Sync) جوه `async def` زي كده:
    response = requests.get("https://api.github.com")
    
    إيه المشكلة اللي هتحصل بالظبط؟
    اللي هيحصل إن `requests.get` هتوّقف الـ Event Loop بالكامل!
    لأنها مافيهاش `await`، السيرفر كله هيعلق ويتجمد لحد ما الطلب يرجع،
    ومش هيقدر يستقبل أي طلبات تانية من أي مستخدم تاني في نفس الوقت (Block the Event Loop).
    """
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.github.com")
    
    return {
        "message": "Fetched from GitHub using async HTTP client",
        "status_code": response.status_code
    }


# --- 3. أمثلة قاعدة البيانات (Database) ---

@router.get("/demo/sync-db")
def sync_db_query():
    """
    مثال على اتصال DB متزامن باستخدام `sqlite3` العادي.
    لأننا استخدمنا `def`، FastAPI هيحط العملية دي في Thread منفصل عشان ما توقفش السيرفر.
    لكن الـ Threads مكلفة لو عندك طلبات كتير جداً.
    """
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute("SELECT 1 AS result")
    result = cursor.fetchone()
    conn.close()
    
    return {"message": "Sync DB query finished", "result": result[0]}

@router.get("/demo/async-db")
async def async_db_query():
    """
    مثال على اتصال DB غير متزامن باستخدام `aiosqlite`.
    هنا بنستخدم `await` مع قاعدة البيانات، فالسيرفر مش بيتعطل أبداً وهو مستني الـ DB ترد.
    هذا هو الأسلوب الأمثل للإنتاج للأداء العالي (High Concurrency).
    """
    async with aiosqlite.connect(':memory:') as db:
        async with db.execute("SELECT 1 AS result") as cursor:
            row = await cursor.fetchone()
            
    return {"message": "Async DB query finished", "result": row[0]}
