from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Optional, Literal, List
from uuid import UUID

# --- Drug Schemas ---

class DrugBase(BaseModel):
    name: str = Field(..., min_length=2)
    category: str
    is_chronic: bool = False
    base_price: float = Field(..., gt=0)
    default_cycle_days: int = Field(30, ge=1)

class DrugCreate(DrugBase):
    image_url: Optional[str] = None

class DrugUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2)
    category: Optional[str] = None
    is_chronic: Optional[bool] = None
    base_price: Optional[float] = Field(None, gt=0)
    default_cycle_days: Optional[int] = Field(None, ge=1)
    image_url: Optional[str] = None

class DrugImageUpdate(BaseModel):
    image_url: Optional[str] = None

class DrugOut(DrugBase):
    drug_id: UUID
    image_url: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class PaginatedDrugsOut(BaseModel):
    items: List[DrugOut]
    total: int
    page: int
    limit: int


# --- Drug Interaction Schemas ---

class DrugInteractionCreate(BaseModel):
    drug_id_a: UUID
    drug_id_b: UUID
    severity: Literal["low", "medium", "high"]
    note: Optional[str] = None

    @model_validator(mode="after")
    def check_different_drugs(self):
        if self.drug_id_a == self.drug_id_b:
            raise ValueError("drug_id_a and drug_id_b must be different (a drug cannot interact with itself)")
        return self

class DrugInteractionOut(BaseModel):
    interaction_id: UUID
    drug_id_a: UUID
    drug_id_b: UUID
    severity: Literal["low", "medium", "high"]
    note: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class CheckInteractionsIn(BaseModel):
    drug_ids: List[UUID]


# --- Drug Affinity Schemas ---

class DrugAffinityCreate(BaseModel):
    drug_id_a: UUID
    drug_id_b: UUID
    affinity_type: Literal["complementary", "market_basket"]
    confidence_score: float = Field(..., ge=0, le=1)

    @model_validator(mode="after")
    def check_different_drugs(self):
        if self.drug_id_a == self.drug_id_b:
            raise ValueError("drug_id_a and drug_id_b must be different (a drug cannot have affinity with itself)")
        return self

class DrugAffinityOut(BaseModel):
    affinity_id: UUID
    drug_id_a: UUID
    drug_id_b: UUID
    affinity_type: Literal["complementary", "market_basket"]
    confidence_score: float
    
    model_config = ConfigDict(from_attributes=True)
