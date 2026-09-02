from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from . import schemas
from . import service

router = APIRouter()

# TODO: Add API Key authentication for internal n8n routes before production.

from app.worker import recalculate_cycles_task
from app.core.rate_limit import limiter
from fastapi import Request

@router.post("/recalculate", response_model=dict)
@limiter.limit("5/minute")
async def recalculate_all_cycles_endpoint(
    request: Request
):
    """
    Internal endpoint: Recalculates average purchase cycles and next reminder days
    for all customers and drugs based on their historical completed orders.
    Triggered via n8n.
    Now dispatched via Celery to prevent blocking the API.
    """
    task = recalculate_cycles_task.delay()
    return {"message": "Recalculation started in the background", "task_id": task.id}

@router.get("/due-reminders", response_model=List[schemas.GroupedReminderOut])
async def get_due_reminders_endpoint(
    tenant_id: UUID = Query(..., description="The tenant ID to query for reminders"),
    db: AsyncSession = Depends(get_db)
):
    """
    Internal endpoint: Retrieves a list of customers who are due for a reminder today.
    Excludes customers who already received a reminder in the last 24 hours.
    Triggered via n8n.
    """
    return await service.get_customers_due_for_reminder(db, tenant_id)
