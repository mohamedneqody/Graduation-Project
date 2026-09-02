from typing import List
from uuid import UUID
from datetime import date
from pydantic import BaseModel

class RecalculationSummary(BaseModel):
    updated_count: int
    created_count: int
    total_processed: int

class DueDrug(BaseModel):
    drug_id: UUID
    drug_name: str
    avg_cycle_days: float
    reminder_day: date

class GroupedReminderOut(BaseModel):
    customer_id: UUID
    preferred_channel: str
    customer_contact: str
    is_fallback_contact: bool
    due_drugs: List[DueDrug]
