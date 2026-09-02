from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class TenantSettingsBase(BaseModel):
    ai_review_mode: bool = True
    enterprise_notifications: bool = False

class TenantSettingsUpdate(BaseModel):
    ai_review_mode: Optional[bool] = None
    enterprise_notifications: Optional[bool] = None

class TenantSettingsOut(TenantSettingsBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
