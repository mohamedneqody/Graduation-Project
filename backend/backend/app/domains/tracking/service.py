from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.session import Session, Event
from app.domains.tracking.schemas import EventCreate

async def log_event(db: AsyncSession, session_id: UUID, event_data: EventCreate) -> Event:
    """Creates a new Event row linked to the passed session_id."""
    new_event = Event(
        session_id=session_id,
        event_type=event_data.event_type,
        payload=event_data.payload
    )
    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)
    return new_event

async def link_session_to_customer(db: AsyncSession, session_id: UUID, customer_id: UUID) -> None:
    """
    Called upon successful login/registration.
    Updates session.customer_id so past and future events are linked to the user.
    """
    result = await db.execute(select(Session).where(Session.session_id == session_id))
    session = result.scalars().first()
    
    if session and session.customer_id != customer_id:
        session.customer_id = customer_id
        await db.commit()

async def get_customer_recent_events(db: AsyncSession, customer_id: UUID, limit: int = 20) -> list[Event]:
    """Returns the most recent behavioral events for a customer across all their sessions."""
    result = await db.execute(
        select(Event)
        .join(Session, Session.session_id == Event.session_id)
        .where(Session.customer_id == customer_id)
        .order_by(desc(Event.timestamp))
        .limit(limit)
    )
    return list(result.scalars().all())
