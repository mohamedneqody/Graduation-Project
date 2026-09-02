from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.routers.enterprise import limiter

from app.core.config import settings
from app.routers import products, auth
from app.database.session import engine
from app.models.base import Base

# Create tables in dev db
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME)

app.include_router(products.router)
app.include_router(auth.router)

app.include_router(ai.router)

app.include_router(webhooks.router)

from fastapi import APIRouter
from sqlalchemy.orm import Session
from fastapi import Depends
from app.database.session import get_db

health_router = APIRouter(prefix="/api/v1", tags=["Monitoring"])

@health_router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Endpoint لفحص حالة السيرفر وقاعدة البيانات.
    أنظمة الـ Monitoring تحتاجه لتعرف متى يكون السيرفر جاهزاً للعمل (Ready) ومتى يموت (Dead) لتعيد تشغيله.
    """
    db_status = "ok"
    try:
        # فحص فعلي لقاعدة البيانات
        db.execute("SELECT 1")
    except Exception:
        db_status = "down"
    
    status_code = 200 if db_status == "ok" else 503
    
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=status_code, content={"status": "up", "database": db_status})

app.include_router(health_router)

import asyncio
from app.services.enterprise import background_worker

@app.on_event("startup")
async def startup_event():
    # تشغيل الـ Worker الخاص بالطابور (Queue) في الخلفية
    asyncio.create_task(background_worker())
