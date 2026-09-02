import uuid
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class PrescriptionCreateResponse(BaseModel):
    prescription_id: uuid.UUID

class PrescriptionItemSchema(BaseModel):
    id: uuid.UUID
    raw_name: Optional[str] = None
    normalized_name: Optional[str] = None
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    quantity: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None
    ocr_confidence: Optional[float] = None
    is_illegible: bool
    match_status: str
    matched_drug_id: Optional[uuid.UUID] = None
    match_confidence: Optional[float] = None
    candidate_margin: Optional[float] = None
    candidates: Optional[list] = None
    pharmacist_decision: str
    pharmacist_selected_drug_id: Optional[uuid.UUID] = None
    
    class Config:
        orm_mode = True

class PrescriptionAnalysisSchema(BaseModel):
    id: uuid.UUID
    prescription_id: uuid.UUID
    file_id: Optional[str] = None
    status: str
    provider: str
    model: str
    items: List[PrescriptionItemSchema] = []
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True

class PharmacistReviewRequest(BaseModel):
    decision: str = Field(..., description="confirmed | rejected | overridden")
    selected_drug_id: Optional[uuid.UUID] = None
