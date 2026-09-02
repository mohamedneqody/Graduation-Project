from pydantic import BaseModel
from typing import Optional

class MarketingRequest(BaseModel):
    customer_name: str
    drug_name: str
    discount_percentage: Optional[int] = None

class MarketingResponse(BaseModel):
    message_text: str
    coupon_code: Optional[str]
    llm_source: str

class PricingRequest(BaseModel):
    customer_name: str
    churn_probability: float
    order_count: int

class PricingResponse(BaseModel):
    discount_percentage: int
    rationale: str
    llm_source: str

class ExecutiveRequest(BaseModel):
    query: str
    context_data: Optional[dict] = None

class ExecutiveResponse(BaseModel):
    routed_to: str
    response_text: str
    llm_source: str
