from typing import List, Tuple, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, asc, desc
from sqlalchemy.exc import IntegrityError
from app.models.drug import Drug, DrugInteraction, DrugAffinity
from app.models.order import OrderItem
from app.core.exceptions import NotFoundError, ConflictError, BusinessRuleViolation
from . import schemas

# --- Drugs ---

async def create_drug(db: AsyncSession, drug_data: schemas.DrugCreate) -> Drug:
    db_drug = Drug(**drug_data.model_dump())
    db.add(db_drug)
    await db.commit()
    await db.refresh(db_drug)
    return db_drug

async def get_drug(db: AsyncSession, drug_id: UUID) -> Drug:
    result = await db.execute(select(Drug).where(Drug.drug_id == drug_id))
    drug = result.scalars().first()
    if not drug:
        raise NotFoundError(resource_name="Drug", resource_id=str(drug_id))
    return drug

async def list_drugs(
    db: AsyncSession, 
    page: int, 
    limit: int, 
    category: Optional[str] = None, 
    is_chronic: Optional[bool] = None,
    search: Optional[str] = None,
    sort_by: str = "name", 
    sort_order: str = "asc"
) -> Tuple[List[Drug], int]:
    query = select(Drug)
    
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            (Drug.name.ilike(search_pattern)) | 
            (Drug.category.ilike(search_pattern))
        )
    if category and category != "All":
        query = query.where(Drug.category == category)
    if is_chronic is not None:
        query = query.where(Drug.is_chronic == is_chronic)
        
    # Get total count before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Apply sorting safely
    if sort_by not in ["name", "base_price", "default_cycle_days"]:
        sort_by = "name"
        
    sort_col = getattr(Drug, sort_by)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_col))
    else:
        query = query.order_by(asc(sort_col))
        
    # Apply pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    drugs = result.scalars().all()
    
    return list(drugs), total

async def get_categories(db: AsyncSession) -> List[dict]:
    query = select(Drug.category, func.count(Drug.drug_id).label("count")).group_by(Drug.category).order_by(desc("count"))
    res = await db.execute(query)
    return [{"name": row.category, "count": row.count} for row in res.all()]

async def get_recommendations(db: AsyncSession, limit: int = 4) -> List[Drug]:
    aff_res = await db.execute(
        select(DrugAffinity.drug_id_b, func.max(DrugAffinity.confidence_score).label("max_score"))
        .group_by(DrugAffinity.drug_id_b)
        .order_by(desc("max_score"))
        .limit(limit)
    )
    drug_ids = [r[0] for r in aff_res.all()]
    recs: List[Drug] = []
    if drug_ids:
        res = await db.execute(select(Drug).where(Drug.drug_id.in_(drug_ids)))
        recs = list(res.scalars().all())
    
    if len(recs) < limit:
        remaining = limit - len(recs)
        rec_ids = [d.drug_id for d in recs]
        fallback_query = select(Drug)
        if rec_ids:
            fallback_query = fallback_query.where(Drug.drug_id.not_in(rec_ids))
        fallback_query = fallback_query.order_by(desc(Drug.base_price)).limit(remaining)
        fallback_res = await db.execute(fallback_query)
        recs = recs + list(fallback_res.scalars().all())
    return recs

async def update_drug(db: AsyncSession, drug_id: UUID, data: schemas.DrugUpdate) -> Drug:
    drug = await get_drug(db, drug_id)
    update_data = data.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(drug, key, value)
        
    await db.commit()
    await db.refresh(drug)
    return drug

async def update_drug_image(db: AsyncSession, drug_id: UUID, image_url: Optional[str]) -> Drug:
    drug = await get_drug(db, drug_id)
    drug.image_url = image_url
    await db.commit()
    await db.refresh(drug)
    return drug

async def delete_drug(db: AsyncSession, drug_id: UUID) -> None:
    drug = await get_drug(db, drug_id)
    
    # Check if there are any order_items referencing this drug
    # We use limit(1) for an efficient existence check
    result = await db.execute(select(OrderItem).where(OrderItem.drug_id == drug_id).limit(1))
    if result.scalars().first():
        raise BusinessRuleViolation(
            detail="Cannot delete this drug because it is referenced in existing orders. Consider soft-deleting by updating its status or price."
        )
        
    await db.delete(drug)
    await db.commit()

# --- Drug Interactions ---

async def create_interaction(db: AsyncSession, data: schemas.DrugInteractionCreate) -> DrugInteraction:
    # Auto-sort the UUIDs so a < b
    u1, u2 = data.drug_id_a, data.drug_id_b
    drug_id_a, drug_id_b = (u1, u2) if u1 < u2 else (u2, u1)
    
    interaction = DrugInteraction(
        drug_id_a=drug_id_a,
        drug_id_b=drug_id_b,
        severity=data.severity,
        note=data.note
    )
    
    try:
        db.add(interaction)
        await db.commit()
        await db.refresh(interaction)
        return interaction
    except IntegrityError:
        await db.rollback()
        raise ConflictError(detail="This drug interaction already exists.")

async def check_interactions(db: AsyncSession, drug_ids: List[UUID]) -> List[DrugInteraction]:
    if len(drug_ids) < 2:
        return []
        
    # Because of the a < b constraint, any interaction between drugs in the list
    # will have BOTH drug_id_a and drug_id_b inside this list.
    query = select(DrugInteraction).where(
        DrugInteraction.drug_id_a.in_(drug_ids),
        DrugInteraction.drug_id_b.in_(drug_ids)
    )
    
    result = await db.execute(query)
    return list(result.scalars().all())

# --- Drug Affinities ---

async def create_affinity(db: AsyncSession, data: schemas.DrugAffinityCreate) -> DrugAffinity:
    # Auto-sort the UUIDs so a < b
    u1, u2 = data.drug_id_a, data.drug_id_b
    drug_id_a, drug_id_b = (u1, u2) if u1 < u2 else (u2, u1)
    
    affinity = DrugAffinity(
        drug_id_a=drug_id_a,
        drug_id_b=drug_id_b,
        affinity_type=data.affinity_type,
        confidence_score=data.confidence_score
    )
    
    try:
        db.add(affinity)
        await db.commit()
        await db.refresh(affinity)
        return affinity
    except IntegrityError:
        await db.rollback()
        raise ConflictError(detail="This drug affinity already exists.")

async def list_affinities_for_drug(db: AsyncSession, drug_id: UUID) -> List[DrugAffinity]:
    # A drug can be in either drug_id_a or drug_id_b
    query = select(DrugAffinity).where(
        (DrugAffinity.drug_id_a == drug_id) | (DrugAffinity.drug_id_b == drug_id)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_cross_sell(db: AsyncSession, drug_id: UUID, limit: int = 5) -> list:
    """
    Cross-sell (FR-11): يُرجع الأدوية المُقترَحة لدواء معين
    بناءً على جدول drug_affinities، مرتَّبة تنازلياً بـ confidence_score.
    يُرجع اسم الدواء المُقترَح + نوع الـ affinity + درجة الثقة.
    """
    from sqlalchemy import alias
    DrugA = alias(Drug, name="drug_a")
    DrugB = alias(Drug, name="drug_b")

    # Affinities where this drug is drug_id_a
    q1 = (
        select(
            DrugAffinity.affinity_id,
            DrugAffinity.affinity_type,
            DrugAffinity.confidence_score,
            Drug.drug_id.label("recommended_drug_id"),
            Drug.name.label("recommended_drug_name"),
            Drug.category.label("recommended_category"),
            Drug.base_price.label("recommended_price"),
        )
        .join(Drug, Drug.drug_id == DrugAffinity.drug_id_b)
        .where(DrugAffinity.drug_id_a == drug_id)
    )

    # Affinities where this drug is drug_id_b
    q2 = (
        select(
            DrugAffinity.affinity_id,
            DrugAffinity.affinity_type,
            DrugAffinity.confidence_score,
            Drug.drug_id.label("recommended_drug_id"),
            Drug.name.label("recommended_drug_name"),
            Drug.category.label("recommended_category"),
            Drug.base_price.label("recommended_price"),
        )
        .join(Drug, Drug.drug_id == DrugAffinity.drug_id_a)
        .where(DrugAffinity.drug_id_b == drug_id)
    )

    from sqlalchemy import union_all, text as sqla_text
    combined = union_all(q1, q2).alias("combined")
    final_q = select(combined).order_by(combined.c.confidence_score.desc()).limit(limit)

    rows = (await db.execute(final_q)).all()
    return [
        {
            "recommended_drug_id": str(r.recommended_drug_id),
            "recommended_drug_name": r.recommended_drug_name,
            "category": r.recommended_category,
            "base_price": float(r.recommended_price),
            "affinity_type": r.affinity_type,
            "confidence_score": r.confidence_score,
        }
        for r in rows
    ]
