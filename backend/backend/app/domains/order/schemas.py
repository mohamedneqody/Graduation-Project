from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal, Optional
from uuid import UUID
from datetime import datetime, date

class OrderItemCreate(BaseModel):
    drug_id: UUID
    quantity: int = Field(..., ge=1)

class OrderCreate(BaseModel):
    items: List[OrderItemCreate] = Field(..., min_length=1)
    channel: Literal["web", "whatsapp", "app"]

class OrderItemOut(BaseModel):
    order_item_id: UUID
    drug_id: UUID
    drug_name: str
    quantity: int
    price: float
    subtotal: float
    
    model_config = ConfigDict(from_attributes=True)

class OrderOut(BaseModel):
    order_id: UUID
    order_date: datetime
    status: str
    channel: str
    items: List[OrderItemOut]
    total_amount: float
    warnings: List[str] = Field(default_factory=list)
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class PaginatedOrdersOut(BaseModel):
    items: List[OrderOut]
    total: int
    page: int
    limit: int

class OrderStatusUpdate(BaseModel):
    status: Literal["pending", "completed", "cancelled"]
