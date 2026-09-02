from fastapi import APIRouter, UploadFile, File, BackgroundTasks, status
from . import schemas, service

router = APIRouter()

@router.post("/upload", response_model=schemas.FileUploadOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Endpoint for uploading a file (Image/PDF).
    It saves the file and triggers a background task for processing (e.g., OCR).
    """
    result = await service.handle_file_upload(file)
    
    # Trigger background task
    background_tasks.add_task(service.process_file_in_background, file.filename)
    
    return result

from fastapi.responses import FileResponse
import os
from app.dependencies.auth import get_current_user
from app.models.customer import Customer
from app.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.models.tracking import AuditLog

@router.get("/{filename}")
async def get_file(
    filename: str,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select
    from app.models.prescription import Prescription
    from fastapi import HTTPException
    
    file_path = f"uploads/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    # Security: Authorize file access
    presc_res = await db.execute(select(Prescription).where(Prescription.file_id == filename))
    prescription = presc_res.scalars().first()
    
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription file not found in database")
        
    is_owner = current_user.auth_user_id == prescription.uploaded_by
    is_authorized_staff = current_user.role in ["pharmacist", "admin"] and current_user.tenant_id == prescription.tenant_id
    
    if not (is_owner or is_authorized_staff):
        raise HTTPException(status_code=403, detail="Not authorized to view this prescription")
        
    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        action_type="prescription_image_viewed",
        target_entity=f"file:{filename}",
        actor_id=str(current_user.auth_user_id)
    )
    db.add(audit)
    await db.commit()
    
    return FileResponse(file_path)
