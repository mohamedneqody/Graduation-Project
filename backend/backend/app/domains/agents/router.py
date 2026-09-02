from fastapi import APIRouter
from app.domains.agents import schemas
from app.domains.agents import marketing, pricing, executive

router = APIRouter()

@router.post("/marketing/generate-campaign", response_model=schemas.MarketingResponse)
async def generate_campaign(request: schemas.MarketingRequest):
    """
    Calls the Marketing Agent to generate a promotional message and coupon.
    """
    result = await marketing.generate_marketing_campaign(
        customer_name=request.customer_name,
        drug_name=request.drug_name,
        discount=request.discount_percentage
    )
    return result

@router.post("/pricing/calculate-discount", response_model=schemas.PricingResponse)
async def calculate_discount(request: schemas.PricingRequest):
    """
    Calls the Pricing Agent to determine the best discount for a user.
    """
    result = await pricing.calculate_pricing_discount(
        customer_name=request.customer_name,
        churn_probability=request.churn_probability,
        order_count=request.order_count
    )
    return result

@router.post("/executive/chat", response_model=schemas.ExecutiveResponse)
async def executive_chat(request: schemas.ExecutiveRequest):
    """
    Calls the Executive Agent to route a general query.
    """
    result = await executive.execute_query(
        query=request.query,
        context_data=request.context_data
    )
    return result
