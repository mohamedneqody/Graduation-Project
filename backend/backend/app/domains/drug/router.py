from fastapi import APIRouter, Depends, Query, Path, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from fastapi_cache.decorator import cache
from app.database.session import get_db
from app.core.exceptions import BusinessRuleViolation
from app.core.rate_limit import limiter
from app.models.session import Session
from app.dependencies.session import get_or_create_session
from . import schemas, service
from fastapi_cache.key_builder import default_key_builder

def cache_key_builder(func, namespace: str = "", *, request=None, response=None, args=(), kwargs={}):
    # Exclude non-cacheable dependencies like DB connections and sessions
    kwargs_copy = {k: v for k, v in kwargs.items() if k not in ["db", "session", "request"]}
    return default_key_builder(func, namespace, request=request, response=response, args=args, kwargs=kwargs_copy)

router = APIRouter()
internal_router = APIRouter()

# --- Drugs ---

@router.post("/", response_model=schemas.DrugOut, status_code=status.HTTP_201_CREATED)
async def create_drug(
    drug_in: schemas.DrugCreate,
    db: AsyncSession = Depends(get_db)
):
    return await service.create_drug(db, drug_in)

@router.get("/categories")
@cache(expire=3600, key_builder=cache_key_builder)
async def get_categories(
    db: AsyncSession = Depends(get_db)
):
    return await service.get_categories(db)

@router.get("/recommendations", response_model=List[schemas.DrugOut])
@cache(expire=3600, key_builder=cache_key_builder)
async def get_recommendations(
    limit: int = Query(4, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    return await service.get_recommendations(db, limit=limit)

@router.get("/", response_model=schemas.PaginatedDrugsOut)
@cache(expire=60, key_builder=cache_key_builder)
@limiter.limit("60/minute")
async def list_drugs(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_chronic: Optional[bool] = Query(None, description="Filter by chronic status"),
    search: Optional[str] = Query(None, description="Search term for drug name or category"),
    sort_by: str = Query("name", description="Field to sort by (name, base_price, default_cycle_days)"),
    sort_order: str = Query("asc", description="Sort order (asc or desc)"),
    db: AsyncSession = Depends(get_db)
):
    items, total = await service.list_drugs(
        db, page=page, limit=limit, category=category, is_chronic=is_chronic,
        search=search, sort_by=sort_by, sort_order=sort_order
    )
    return schemas.PaginatedDrugsOut(
        items=items,
        total=total,
        page=page,
        limit=limit
    )

from app.domains.tracking.service import log_event
from app.domains.tracking.schemas import EventCreate
import asyncio

@router.get("/{drug_id}", response_model=schemas.DrugOut)
async def get_drug(
    drug_id: UUID = Path(...),
    session: Session = Depends(get_or_create_session),
    db: AsyncSession = Depends(get_db)
):
    drug = await service.get_drug(db, drug_id)
    
    # Best-effort tracking
    try:
        await log_event(db, session.session_id, EventCreate(
            event_type="view_drug",
            payload={"drug_id": str(drug_id)}
        ))
    except Exception:
        pass # Ignore tracking failures
        
    return drug

@router.put("/{drug_id}", response_model=schemas.DrugOut)
async def update_drug(
    drug_in: schemas.DrugUpdate,
    drug_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db)
):
    return await service.update_drug(db, drug_id, drug_in)

@router.delete("/{drug_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_drug(
    drug_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db)
):
    await service.delete_drug(db, drug_id)

@internal_router.patch("/{drug_id}/image", response_model=schemas.DrugOut)
async def update_drug_image(
    payload: schemas.DrugImageUpdate,
    drug_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Internal endpoint to update just the image_url of a drug.
    """
    return await service.update_drug_image(db, drug_id, payload.image_url)

# --- Drug Interactions ---

@router.post("/interactions", response_model=schemas.DrugInteractionOut, status_code=status.HTTP_201_CREATED)
async def create_interaction(
    interaction_in: schemas.DrugInteractionCreate,
    db: AsyncSession = Depends(get_db)
):
    return await service.create_interaction(db, interaction_in)

@router.post("/check-interactions", response_model=List[schemas.DrugInteractionOut])
async def check_interactions(
    payload: schemas.CheckInteractionsIn,
    db: AsyncSession = Depends(get_db)
):
    return await service.check_interactions(db, payload.drug_ids)

# --- Drug Affinities ---

@router.post("/affinities", response_model=schemas.DrugAffinityOut, status_code=status.HTTP_201_CREATED)
async def create_affinity(
    affinity_in: schemas.DrugAffinityCreate,
    db: AsyncSession = Depends(get_db)
):
    return await service.create_affinity(db, affinity_in)

@router.get("/{drug_id}/affinities", response_model=List[schemas.DrugAffinityOut])
async def list_affinities(
    drug_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_affinities_for_drug(db, drug_id)


@router.get(
    "/{drug_id}/cross-sell",
    summary="اقتراحات البيع المتقاطع (FR-11)",
    description="يُرجع الأدوية المُقترَحة بناءً على جدول `drug_affinities` مرتَّبة بـ confidence_score.",
)
async def cross_sell(
    drug_id: UUID = Path(..., description="Drug UUID"),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_cross_sell(db, drug_id, limit=limit)
