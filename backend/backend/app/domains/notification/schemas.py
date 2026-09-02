from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel

class HealthCheckOut(BaseModel):
    status: str

class NotificationRecordIn(BaseModel):
    customer_id: UUID
    notification_type: Literal["reminder", "cross_sell"]
    channel: Literal["whatsapp", "email", "sms"]
    status: Literal["sent", "failed"]
    ab_variant: Optional[str] = None
