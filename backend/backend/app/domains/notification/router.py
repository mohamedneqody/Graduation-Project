from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from . import schemas, service

router = APIRouter()

@router.get("/health", response_model=schemas.HealthCheckOut)
async def health_check(db: AsyncSession = Depends(get_db)):
    return await service.check_health(db)

@router.post("/record", status_code=status.HTTP_201_CREATED)
async def record_notification_endpoint(
    record_in: schemas.NotificationRecordIn,
    db: AsyncSession = Depends(get_db)
):
    """
    Internal endpoint: Record a notification sent by n8n.
    Triggered via n8n directly after sending a message to close the loop.
    """
    return await service.record_notification(db, record_in)
