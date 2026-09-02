from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.session import Session
from app.models.customer import Customer
from app.dependencies.session import get_or_create_session
from app.dependencies.auth import get_current_user
from app.domains.tracking.schemas import EventCreate, EventOut
from app.domains.tracking.service import log_event, get_customer_recent_events

events_router = APIRouter()
customer_events_router = APIRouter()

@events_router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    session: Session = Depends(get_or_create_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Called directly by the frontend to log behavioral events.
    """
    return await log_event(db, session.session_id, event_data)


@customer_events_router.get("/me/events", response_model=list[EventOut])
async def get_my_events(
    limit: int = 20,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the current user's recent events across all their sessions.
    """
    return await get_customer_recent_events(db, current_user.customer_id, limit)
