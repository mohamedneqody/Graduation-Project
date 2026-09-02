import os
import re

base_path = r"d:\Graduation Project\learn_production_fastapi"

files = {
    "app/core/middleware.py": '''"""
# مسؤوليته:
# تعريف الـ Middlewares الخاصة بالتطبيق.
# الـ Middleware هو كود يعمل كـ (حاجز) يعبر عليه كل Request قبل أن يصل للـ Endpoint، 
# ويعبر عليه كل Response قبل أن يعود للمستخدم.
"""
import time
import logging
from fastapi import Request

# 1. Custom Middleware 1: Logging & Timing
async def request_logging_and_timing_middleware(request: Request, call_next):
    """
    هذا الـ Middleware يطبع معلومات عن الطلب (Method + Path + Start Time)،
    ويحسب الزمن المستغرق لإتمام الطلب (X-Process-Time).
    """
    # [قبل وصول الطلب للـ Endpoint]
    start_time = time.perf_counter()
    logging.info(f"Incoming Request: {request.method} {request.url.path} at {start_time}")
    
    # تمرير الطلب للـ Endpoint (أو للـ Middleware التالي)
    response = await call_next(request)
    
    # [بعد عودة الرد من الـ Endpoint]
    process_time = time.perf_counter() - start_time
    process_time_ms = round(process_time * 1000, 2)
    
    # إضافة Header جديد للـ Response يحتوي على الزمن بالميلي ثانية
    response.headers["X-Process-Time"] = f"{process_time_ms} ms"
    
    logging.info(f"Completed Request: {request.method} {request.url.path} in {process_time_ms} ms")
    return response


# 2. Custom Middleware 2: Dummy Middleware for ordering test
async def dummy_middleware(request: Request, call_next):
    """
    هذا الـ Middleware موجود فقط لإثبات فكرة الترتيب.
    """
    logging.info("--> [Dummy Middleware] Request passed through Dummy")
    response = await call_next(request)
    logging.info("<-- [Dummy Middleware] Response passed back through Dummy")
    return response
'''
}

for rel_path, content in files.items():
    full_path = os.path.join(base_path, rel_path.replace("/", os.sep))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

# Update main.py
main_py_path = os.path.join(base_path, "app/main.py")
with open(main_py_path, "r", encoding="utf-8") as f:
    main_content = f.read()

# We want to replace the app creation with middlewares included
new_main_content = '''"""
# مسؤوليته: 
# هذا الملف هو نقطة الدخول (Entry Point) لتطبيق FastAPI.
# يقوم بتجميع كل الـ Routers، إعداد الـ CORS، وتشغيل إعدادات الـ Logging.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import request_logging_and_timing_middleware, dummy_middleware
from app.routers import products, demo_async, files, tasks

# تفعيل الـ Logging
setup_logging()

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

# ترتيب الـ Middlewares في FastAPI (الأحدث إضافة (add_middleware) هو الذي يحيط بالأقدم)
# الترتيب الفعلي من الخارج للداخل (من الأقرب للمستخدم إلى الأقرب للـ Endpoint):
# 1. CORSMiddleware
# 2. dummy_middleware
# 3. request_logging_and_timing_middleware

# إضافة CORSMiddleware المدمج
app.add_middleware(
    CORSMiddleware,
    # allow_origins: السماح للمتصفح بقراءة البيانات لو جاء الطلب من هذه الدومينات فقط. 
    # ["*"] تعني السماح لأي دومين (غير آمن في الإنتاج، يُفضل تحديد دومين الواجهة الأمامية مثل "https://frontend.com").
    allow_origins=["*"],
    
    # allow_credentials: لو الواجهة الأمامية تحتاج إرسال كوكيز (Cookies) أو توكن مع الـ Request.
    # لو وضعتها True، لا يمكنك وضع allow_origins=["*"] (اعتبارات أمنية في المتصفحات).
    allow_credentials=False,
    
    # allow_methods: تحديد الـ HTTP Methods المسموحة (مثل GET, POST). ["*"] تعني السماح بالكل.
    allow_methods=["*"],
    
    # allow_headers: تحديد الـ Headers التي يمكن للعميل إرسالها.
    allow_headers=["*"],
)

# إضافة Custom Middlewares
# في FastAPI عبر add_middleware، الـ Middleware الذي نكتبه أخيراً هو الذي يتم تنفيذه "أولاً" كطبقة خارجية.
from starlette.middleware.base import BaseHTTPMiddleware

# سيتم تنفيذ هذا ثانياً
app.add_middleware(BaseHTTPMiddleware, dispatch=dummy_middleware)

# سيتم تنفيذ هذا أولاً (لأنه الأحدث) بعد الـ CORS
app.add_middleware(BaseHTTPMiddleware, dispatch=request_logging_and_timing_middleware)

# تسجيل الـ Routers
app.include_router(products.router, prefix="/api/v1")
app.include_router(demo_async.router)
app.include_router(files.router)
app.include_router(tasks.router)
'''

with open(main_py_path, "w", encoding="utf-8") as f:
    f.write(new_main_content)

print("Middlewares configured.")
