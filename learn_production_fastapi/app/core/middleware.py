"""
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
