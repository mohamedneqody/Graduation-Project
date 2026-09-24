from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.rate_limit import limiter
import uuid
from datetime import datetime, timezone

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.customer import Customer
from app.models.drug import Drug
from app.models.prescription import Prescription, PrescriptionAnalysis, PrescriptionItem
from app.domains.files.service import handle_file_upload
from .schemas import PrescriptionCreateResponse, PrescriptionAnalysisSchema, PharmacistReviewRequest
from .vision import LocalTrOCRVisionProvider

# Add a provider selection block inside the endpoint

from .matching import match_medication, normalize_text
from app.models.tracking import AuditLog

router = APIRouter(prefix="/api/v1/prescriptions", tags=["Prescriptions"])


@router.post("")
@router.post("/", response_model=PrescriptionCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def upload_prescription(
    request: Request,
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

@router.post("/{id}/analyze")
@limiter.limit("10/minute")
async def analyze_prescription(
    request: Request,
    id: uuid.UUID,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    presc_result = await db.execute(select(Prescription).where(Prescription.id == id))
    prescription = presc_result.scalars().first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    if prescription.uploaded_by != current_user.auth_user_id and current_user.role not in ("admin", "super_admin", "pharmacist"):
        raise HTTPException(status_code=404, detail="Prescription not found")
        
    file_path = f"uploads/{prescription.file_id}"
    import os
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    import hashlib
    sha256_ocr_input = hashlib.sha256(file_bytes).hexdigest()

    drugs_res = await db.execute(select(Drug))
    all_drugs = drugs_res.scalars().all()
    
    # 100% Offline On-Premise Enforcement:
    # Prescription vision analysis is strictly handled by local OCR (Florence-2 + TrOCR).
    # Zero cloud egress, ensuring patient PHI never leaves the local pharmacy network.
    vision_provider = LocalTrOCRVisionProvider()
        
    analysis = PrescriptionAnalysis(
        prescription_id=prescription.id,
        provider="local_trocr",
        model=vision_provider.model,
        schema_version="v1",
        status="pending"
    )
    db.add(analysis)
    await db.flush()
    
    # Catch any error so it doesn't cause a CORS failure on the frontend
    try:
        vision_output, metadata = await vision_provider.analyze_image(file_bytes, "image/jpeg")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="OCR processing failed. Please try again later.")
    
    fingerprint = vision_output.image_fingerprint.model_dump() if vision_output.image_fingerprint else {}
    checkpoint_2 = vision_output.pipeline_hashes.get("checkpoint_2_ocr_receive") or fingerprint.get("sha256")
    checkpoint_3 = vision_output.pipeline_hashes.get("checkpoint_3_trocr_input")
    if checkpoint_2 != sha256_ocr_input or checkpoint_3 != sha256_ocr_input:
        raise HTTPException(
            status_code=502,
            detail="OCR integrity check failed; image bytes changed between pipeline stages.",
        )

    analysis.status = "succeeded"
    analysis.raw_response = vision_output.model_dump()
    analysis.model_version = metadata.model_version
    analysis.prompt_version = metadata.prompt_version
    analysis.request_id = metadata.request_id
    analysis.latency_ms = metadata.latency_ms
    analysis.token_usage = metadata.token_usage
    await db.commit()
    
    from app.domains.prescriptions.matching import match_medication, normalize_text
    
    items = []
    for med in vision_output.medications:
        # 1. Reject entries where visual evidence is false (fail-closed)
        if not getattr(med, "visual_evidence_ok", True):
            continue
        # 2. Reject short fragments
        if getattr(med, "is_fragment_too_short", False):
            continue

        # Skip items with no usable name (OCR noise/blank lines)
        usable_name = (med.raw_name or "").strip()
        if not usable_name or len(usable_name) <= 2:
            continue
        
        match_result = match_medication(med, all_drugs)
        
        final_score = match_result.get("final_score", 0.0)
        candidate_margin = match_result.get("candidate_margin", 0.0)
        match_status = match_result.get("match_status", "needs_review")

        # Disagreement between Florence-2 and TrOCR is a clinical stop condition (caps at 0.70 -> Yellow)
        if getattr(med, "model_disagreement", False):
            final_score = min(final_score, 0.70)
            match_status = "needs_review"
            for candidate in match_result.get("candidates", []):
                candidate["model_disagreement"] = True
                candidate["match_reason"] = "model_disagreement"
        
        if getattr(med, "is_illegible", False):
            match_status = "illegible"

        # A NOT-FOUND line with weak or contradicted OCR evidence is a
        # MISREADING, not a confirmed unavailable drug. Presenting it to the
        # customer as "written in the prescription but out of stock" asserts a
        # reading we cannot back. Fail-safe: route it to the pharmacist review
        # queue (the crop image is attached for manual identification).
        if match_status == "not_found" and (
            getattr(med, "model_disagreement", False)
            or getattr(med, "ocr_confidence", 0.0) < 0.85
        ):
            match_status = "needs_review"

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
            matched_drug_id=match_result.get("matched_drug_id") if match_status == "matched" else None,
            match_confidence=final_score,
            candidate_margin=candidate_margin,
            candidates=match_result.get("candidates", []),
            cropped_image=med.cropped_image,
        )
        db.add(item)
        items.append(item)
        
    await db.commit()
    
    audit = AuditLog(tenant_id=current_user.tenant_id, action_type="prescription_analyzed", target_entity=f"prescription:{prescription.id}", actor_id=str(current_user.customer_id))
    db.add(audit)
    await db.commit()
    
    fingerprint = fingerprint or {
        "sha256": sha256_ocr_input,
        "top_left_visible_text": "N/A",
        "clinic_name_guess": "Unknown",
        "patient_name_guess": "Unknown",
        "approximate_image_orientation": "portrait",
        "number_of_handwritten_lines_visible": len(items)
    }

    return {
        "image_fingerprint": fingerprint,
        "pipeline_hashes": {
            "checkpoint_1_stored_file": sha256_ocr_input,
            "checkpoint_1_ocr_input": sha256_ocr_input,
            "checkpoint_2_ocr_receive": checkpoint_2,
            "checkpoint_3_trocr_input": checkpoint_3,
        },
        "analysis_id": analysis.id,
        "status": "succeeded",
        "provider": analysis.provider,
        "model": analysis.model,
        "items": [
            {
                "id": str(it.id),
                # PrescriptionModal reads raw_name (not raw_text)
                "raw_name": it.raw_name,
                "raw_text": it.raw_name,   # keep backward compat
                "strength": it.strength,
                "dosage_form": it.dosage_form,
                "instructions": it.instructions,
                "ocr_confidence": it.ocr_confidence,
                "is_illegible": it.is_illegible,
                # PrescriptionModal reads match_status (not status)
                "match_status": it.match_status,
                "status": it.match_status,  # keep backward compat
                "matched_drug_id": str(it.matched_drug_id) if it.matched_drug_id else None,
                "drug_id": str(it.matched_drug_id) if it.matched_drug_id else None,
                "match_confidence": it.match_confidence,
                "score": it.match_confidence,
                "candidates": it.candidates or [],
                "cropped_image": it.cropped_image,
            } for it in items
        ]
    }

@router.get("/{id}/analysis", response_model=PrescriptionAnalysisSchema)
async def get_latest_analysis(
    id: uuid.UUID,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    presc_res = await db.execute(select(Prescription).where(Prescription.id == id, Prescription.tenant_id == current_user.tenant_id))
    prescription = presc_res.scalars().first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    if prescription.uploaded_by != current_user.auth_user_id and current_user.role not in ("admin", "super_admin", "pharmacist"):
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
    audit = AuditLog(tenant_id=current_user.tenant_id, action_type="prescription_viewed", target_entity=f"prescription:{id}", actor_id=str(current_user.customer_id))
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
        
    # Enforce tenant scoping and parent association
    item_res = await db.execute(
        select(PrescriptionItem)
        .join(PrescriptionAnalysis, PrescriptionItem.analysis_id == PrescriptionAnalysis.id)
        .join(Prescription, PrescriptionAnalysis.prescription_id == Prescription.id)
        .where(
            PrescriptionItem.id == item_id,
            Prescription.id == id,
            Prescription.tenant_id == current_user.tenant_id
        )
    )
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
    item.reviewed_at = datetime.now(timezone.utc)
    
    audit = AuditLog(tenant_id=current_user.tenant_id, action_type="pharmacist_reviewed_item", target_entity=f"prescription_item:{item.id}", actor_id=str(current_user.customer_id))
    db.add(audit)
    await db.commit()
    return {"message": "Review recorded"}

@router.post("/{id}/finalize")
async def finalize_prescription(
    id: uuid.UUID,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    presc_res = await db.execute(select(Prescription).where(Prescription.id == id, Prescription.tenant_id == current_user.tenant_id))
    prescription = presc_res.scalars().first()
    
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    if prescription.uploaded_by != current_user.auth_user_id and current_user.role not in ("admin", "super_admin", "pharmacist"):
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
    
    audit = AuditLog(tenant_id=current_user.tenant_id, action_type="prescription_finalized", target_entity=f"prescription:{prescription.id}", actor_id=str(current_user.customer_id))
    db.add(audit)
    await db.commit()
    
    return order_out

async def execute_prescription_retention_cleanup(db: AsyncSession, tenant_id=None) -> dict:
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    
    query = select(Prescription).where(Prescription.created_at < cutoff)
    if tenant_id:
        query = query.where(Prescription.tenant_id == tenant_id)
    presc_res = await db.execute(query)
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
async def cleanup_retention(
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can trigger retention cleanup")
    return await execute_prescription_retention_cleanup(db, tenant_id=current_user.tenant_id if current_user.role != "super_admin" else None)

@router.delete("/{id}")
async def delete_prescription(
    id: uuid.UUID,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["admin", "pharmacist"]:
        raise HTTPException(status_code=403, detail="Only pharmacists can delete")
        
    presc_res = await db.execute(select(Prescription).where(Prescription.id == id, Prescription.tenant_id == current_user.tenant_id))
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
    audit = AuditLog(tenant_id=current_user.tenant_id, action_type="prescription_deleted", target_entity=f"prescription:{id}", actor_id=str(current_user.customer_id))
    db.add(audit)
    
    await db.delete(prescription)
    await db.commit()
    
    return {"message": "Prescription and all related data deleted securely"}
