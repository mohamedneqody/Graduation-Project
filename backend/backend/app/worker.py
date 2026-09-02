import asyncio
from celery import Celery
from app.core.config import settings

# Initialize Celery
celery_app = Celery(
    "pharmacy_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Example task wrapper to run async functions
def run_async(coro):
    return asyncio.run(coro)

@celery_app.task
def recalculate_cycles_task():
    from app.database.session import AsyncSessionLocal
    from app.domains.customer_cycle.service import recalculate_all_cycles
    
    async def _recalculate():
        async with AsyncSessionLocal() as db:
            result = await recalculate_all_cycles(db)
            return result
            
@celery_app.task
def cleanup_prescription_retention_task():
    from app.database.session import AsyncSessionLocal
    from app.domains.prescriptions.router import execute_prescription_retention_cleanup
    
    async def _cleanup():
        async with AsyncSessionLocal() as db:
            result = await execute_prescription_retention_cleanup(db)
            return result
            
    return run_async(_cleanup())

from celery.schedules import crontab

if not hasattr(celery_app.conf, "beat_schedule") or not celery_app.conf.beat_schedule:
    celery_app.conf.beat_schedule = {}

celery_app.conf.beat_schedule.update({
    "cleanup-prescriptions-every-night": {
        "task": "app.worker.cleanup_prescription_retention_task",
        "schedule": crontab(hour=3, minute=0), # Run at 3 AM UTC every day
    },
})
