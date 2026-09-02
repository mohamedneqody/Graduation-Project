from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.customer import Customer
from app.models.drug import Drug
from app.models.prescription import Prescription, PrescriptionAnalysis, PrescriptionItem
from app.domains.files.service import handle_file_upload
from .schemas import PrescriptionCreateResponse, PrescriptionAnalysisSchema, PharmacistReviewRequest
from .vision import GeminiVisionProvider
from .matching import match_medication, normalize_text
from app.models.tracking import AuditLog

router = APIRouter(prefix="/api/v1/prescriptions", tags=["Prescriptions"])

@router.get("/test_route")
async def test_prescriptions_route():
    return {"message": "Prescriptions router is alive"}

@router.post("/", response_model=PrescriptionCreateResponse, status_code=status.HTTP_201_CREATED)
async def upload_prescription(
    file: UploadFile = File(...),
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    file_result = await handle_file_upload(file)
    file_id = file_result.get("filename")
    if not file_id:
        raise HTTPException(status_code=500, detail="Failed to upload file")
        
    new_prescription = Prescription(
        file_id=file_id,
        tenant_id=current_user.tenant_id,
        uploaded_by=current_user.auth_user_id,
        status="uploaded"
    )
    db.add(new_prescription)
    await db.commit()
    await db.refresh(new_prescription)
    return PrescriptionCreateResponse(prescription_id=new_prescription.id)

@router.post("/{id}/analyze", response_model=PrescriptionAnalysisSchema)
async def analyze_prescription(
    id: uuid.UUID,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    presc_result = await db.execute(select(Prescription).where(Prescription.id == id))
    prescription = presc_result.scalars().first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
        
    file_path = f"uploads/{prescription.file_id}"
    import os
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    drugs_res = await db.execute(select(Drug))
    all_drugs = drugs_res.scalars().all()
    
    vision_provider = GeminiVisionProvider()
    
    analysis = PrescriptionAnalysis(
        prescription_id=prescription.id,
        provider="gemini",
        model=vision_provider.model,
        schema_version="v1",
        status="pending"
    )
    db.add(analysis)
    await db.flush()
    
    try:
        vision_output, metadata = await vision_provider.analyze_image(file_bytes, "image/jpeg")
        analysis.status = "succeeded"
        analysis.raw_response = vision_output.model_dump()
        analysis.model_version = metadata.model_version
        analysis.prompt_version = metadata.prompt_version
        analysis.request_id = metadata.request_id
        analysis.latency_ms = metadata.latency_ms
        analysis.token_usage = metadata.token_usage
        
        items = []
        for med in vision_output.medications:
            match_result = match_medication(med, all_drugs)
            match_status = "needs_review"
            final_score = match_result["final_score"]
            candidate_margin = match_result["candidate_margin"]
            
            if med.is_illegible:
                match_status = "illegible"
            elif not match_result["candidates"]:
                match_status = "not_found"
            elif final_score >= 0.90 and candidate_margin is not None and candidate_margin >= 0.10:
                match_status = "matched"
                
            item = PrescriptionItem(
                analysis_id=analysis.id,
                raw_name=med.raw_name,
                normalized_name=normalize_text(med.raw_name),
                strength=med.strength,
                dosage_form=med.dosage_form,
                quantity=med.quantity,
                duration=med.duration,
                instructions=med.instructions,
                ocr_confidence=med.ocr_confidence,
                is_illegible=med.is_illegible,
                match_status=match_status,
                matched_drug_id=match_result["matched_drug_id"] if match_status == "matched" else None,
                match_confidence=final_score,
                candidate_margin=candidate_margin,
                candidates=match_result["candidates"],
                pharmacist_decision="pending"
            )
            db.add(item)
            items.append(item)
            
        prescription.status = "analyzed"
        
        # Audit Log
        audit = AuditLog(
            tenant_id=current_user.tenant_id,
            action="prescription_analyzed",
            entity_type="prescription_analysis",
            entity_id=str(analysis.id),
            actor_id=current_user.customer_id,
            new_values={"provider": "gemini", "status": "succeeded"}
        )
        db.add(audit)
        
        await db.commit()
        await db.refresh(analysis)
        analysis.items = items
        return analysis

    except Exception as e:
        analysis.status = "failed"
        analysis.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Vision API Error: {str(e)}")

@router.get("/{id}/analysis", response_model=PrescriptionAnalysisSchema)
async def get_latest_analysis(
    id: uuid.UUID,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    presc_res = await db.execute(select(Prescription).where(Prescription.id == id))
    prescription = presc_res.scalars().first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    analysis_res = await db.execute(
        select(PrescriptionAnalysis)
        .where(PrescriptionAnalysis.prescription_id == id)
        .order_by(PrescriptionAnalysis.created_at.desc())
    )
    analysis = analysis_res.scalars().first()
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found")
        
    analysis.file_id = prescription.file_id
        
    items_res = await db.execute(select(PrescriptionItem).where(PrescriptionItem.analysis_id == analysis.id))
    analysis.items = items_res.scalars().all()
    
    # Audit log view
    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        action="prescription_viewed",
        entity_type="prescription",
        entity_id=str(id),
        actor_id=current_user.customer_id
    )
    db.add(audit)
    await db.commit()
    
    return analysis

@router.post("/{id}/items/{item_id}/review")
async def review_item(
    id: uuid.UUID,
    item_id: uuid.UUID,
    request: PharmacistReviewRequest,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["admin", "pharmacist"]:
        raise HTTPException(status_code=403, detail="Only pharmacists can review")
        
    item_res = await db.execute(select(PrescriptionItem).where(PrescriptionItem.id == item_id))
    item = item_res.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    if request.decision not in ["confirmed", "rejected", "overridden"]:
        raise HTTPException(status_code=400, detail="Invalid decision value")
        
    if request.decision == "overridden":
        if not request.selected_drug_id:
            raise HTTPException(status_code=400, detail="selected_drug_id required for overridden")
        drug_res = await db.execute(select(Drug).where(Drug.drug_id == request.selected_drug_id))
        if not drug_res.scalars().first():
            raise HTTPException(status_code=400, detail="Invalid selected_drug_id")
        item.pharmacist_selected_drug_id = request.selected_drug_id
        
    item.pharmacist_decision = request.decision
    item.reviewed_by = current_user.auth_user_id
    item.reviewed_at = datetime.utcnow()
    
    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        action="pharmacist_reviewed_item",
        entity_type="prescription_item",
        entity_id=str(item.id),
        actor_id=current_user.customer_id,
        new_values={"decision": request.decision, "selected_drug_id": str(request.selected_drug_id)}
    )
    db.add(audit)
    await db.commit()
    return {"message": "Review recorded"}

@router.post("/{id}/finalize")
async def finalize_prescription(
    id: uuid.UUID,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    presc_res = await db.execute(select(Prescription).where(Prescription.id == id))
    prescription = presc_res.scalars().first()
    
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
        
    if prescription.status == "finalized":
        return {"message": "Already finalized. Cart entries were created previously."}
        
    if prescription.status not in ["analyzed", "reviewed"]:
        raise HTTPException(status_code=400, detail="Prescription not ready for finalize")
        
    subq = select(PrescriptionAnalysis.id).where(PrescriptionAnalysis.prescription_id == id).order_by(PrescriptionAnalysis.created_at.desc()).limit(1).scalar_subquery()
    items_res = await db.execute(select(PrescriptionItem).where(PrescriptionItem.analysis_id == subq))
    items = items_res.scalars().all()
    
    if not items:
        raise HTTPException(status_code=400, detail="No items to finalize")
        
    drug_ids = []
    for item in items:
        if item.pharmacist_decision == "pending":
            raise HTTPException(status_code=400, detail=f"Item {item.id} is still pending review")
            
        if item.pharmacist_decision == "confirmed":
            if not item.matched_drug_id:
                raise HTTPException(status_code=400, detail="Confirmed item has no matched_drug_id")
            drug_ids.append(item.matched_drug_id)
        elif item.pharmacist_decision == "overridden":
            if not item.pharmacist_selected_drug_id:
                raise HTTPException(status_code=400, detail="Overridden item has no selected_drug_id")
            drug_ids.append(item.pharmacist_selected_drug_id)
            
    if not drug_ids:
        return {"message": "No valid items to add to cart"}
        
    drugs_res = await db.execute(select(Drug).where(Drug.drug_id.in_(drug_ids)))
    found_drugs = drugs_res.scalars().all()
    if len(found_drugs) != len(set(drug_ids)):
        raise HTTPException(status_code=400, detail="Some drugs are no longer available in the catalog")
        
    from app.domains.order.schemas import OrderCreate, OrderItemCreate
    from app.domains.order.service import create_order
    
    order_in = OrderCreate(
        items=[OrderItemCreate(drug_id=d_id, quantity=1) for d_id in drug_ids],
        channel="web"
    )
    
    order_out = await create_order(db, current_user.customer_id, current_user.tenant_id, order_in)
    
    prescription.status = "finalized"
    
    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        action="prescription_finalized",
        entity_type="prescription",
        entity_id=str(prescription.id),
        actor_id=current_user.customer_id,
        new_values={"order_id": str(order_out.order_id)}
    )
    db.add(audit)
    await db.commit()
    
    return order_out

async def execute_prescription_retention_cleanup(db: AsyncSession) -> dict:
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=30)
    
    presc_res = await db.execute(select(Prescription).where(Prescription.created_at < cutoff))
    old_prescriptions = presc_res.scalars().all()
    
    count = 0
    import os
    for p in old_prescriptions:
        file_path = f"uploads/{p.file_id}"
        if os.path.exists(file_path):
            os.remove(file_path)
            
        analyses_res = await db.execute(select(PrescriptionAnalysis).where(PrescriptionAnalysis.prescription_id == p.id))
        for analysis in analyses_res.scalars().all():
            items_res = await db.execute(select(PrescriptionItem).where(PrescriptionItem.analysis_id == analysis.id))
            for item in items_res.scalars().all():
                await db.delete(item)
            await db.flush()  # Must flush item deletions before deleting analysis
            await db.delete(analysis)
            
        await db.flush()  # Must flush analysis deletions before deleting prescription
        
        # Add audit log for the automated deletion
        audit = AuditLog(
            tenant_id=p.tenant_id,
            action_type="prescription_deleted_by_retention",
            target_entity=f"prescription:{p.id}",
            actor_id="system_cron"
        )
        db.add(audit)
        
        await db.delete(p)
        count += 1
        
    await db.commit()
    return {"message": f"Deleted {count} old prescriptions as per 30-day retention policy."}

@router.delete("/cleanup-retention")
async def cleanup_retention(db: AsyncSession = Depends(get_db)):
    return await execute_prescription_retention_cleanup(db)

@router.delete("/{id}")
async def delete_prescription(
    id: uuid.UUID,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["admin", "pharmacist"]:
        raise HTTPException(status_code=403, detail="Only pharmacists can delete")
        
    presc_res = await db.execute(select(Prescription).where(Prescription.id == id))
    prescription = presc_res.scalars().first()
    
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
        
    # Delete file if exists
    import os
    file_path = f"uploads/{prescription.file_id}"
    if os.path.exists(file_path):
        os.remove(file_path)
        
    # Explicitly delete child records since cascade isn't configured
    analyses_res = await db.execute(select(PrescriptionAnalysis).where(PrescriptionAnalysis.prescription_id == id))
    analyses = analyses_res.scalars().all()
    for analysis in analyses:
        await db.execute(select(PrescriptionItem).where(PrescriptionItem.analysis_id == analysis.id))
        items_res = await db.execute(select(PrescriptionItem).where(PrescriptionItem.analysis_id == analysis.id))
        items = items_res.scalars().all()
        for item in items:
            await db.delete(item)
        await db.flush()  # Flush item deletions first
        await db.delete(analysis)
        
    await db.flush()  # Flush analysis deletions first
        
    # Log deletion before actually deleting the entity
    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        action="prescription_deleted",
        entity_type="prescription",
        entity_id=str(id),
        actor_id=current_user.customer_id
    )
    db.add(audit)
    
    await db.delete(prescription)
    await db.commit()
    
    return {"message": "Prescription and all related data deleted securely"}
