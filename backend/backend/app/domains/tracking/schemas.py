from typing import Literal, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class EventCreate(BaseModel):
    event_type: Literal["page_view", "search", "add_to_cart", "view_drug", "start_checkout"]
    payload: Optional[dict] = Field(default=None, description="Free-form JSON payload, e.g. {'drug_id': '...', 'query': '...'}")

class EventOut(EventCreate):
    event_id: UUID
    session_id: UUID
    timestamp: datetime
    
    class Config:
        from_attributes = True

class SessionOut(BaseModel):
    session_id: UUID
    customer_id: Optional[UUID] = None
    device_info: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
