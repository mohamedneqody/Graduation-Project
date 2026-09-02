from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID

class HealthCheckOut(BaseModel):
    status: str
    
class CustomerBase(BaseModel):
    email: EmailStr = Field(..., description="Customer's email address")
    full_name: Optional[str] = Field(None, min_length=2, max_length=255, description="Full name of the customer")
    phone: Optional[str] = Field(None, pattern=r"^(\+?[0-9]\d{1,14}|01[0125]\d{8}|\d{10,11})$", description="Phone number")
    age_group: Optional[str] = Field(None, pattern=r"^(child|teen|adult|senior)$", description="Age group categorization")
    preferred_channel: str = Field("email", pattern=r"^(email|sms|whatsapp|push)$")
    preferred_language: str = Field("ar", pattern=r"^(ar|en)$")

class CustomerCreate(CustomerBase):
    auth_user_id: UUID = Field(..., description="Supabase Auth UUID")
    tenant_id: UUID = Field(..., description="Tenant ID to which this customer belongs")

class CustomerUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, pattern=r"^(\+?[0-9]\d{1,14}|01[0125]\d{8}|\d{10,11})$")
    is_active: Optional[bool] = None

class CustomerOut(CustomerBase):
    customer_id: UUID
    tenant_id: UUID
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    total_orders: Optional[int] = 0
    role: Optional[str] = None

    model_config = {"from_attributes": True}
