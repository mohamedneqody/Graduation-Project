from pydantic import BaseModel
from uuid import UUID
from typing import Optional, List


class GovernanceAction(str):
    AUTO_SEND    = "auto_send"         # confidence > 0.80 → تذكير تلقائي
    HUMAN_REVIEW = "human_review"      # 0.50-0.80 → مراجعة بشرية
    COLD_START   = "cold_start"        # < 0.50 → تجاهل / fallback


class GovernanceRequest(BaseModel):
    customer_id: UUID
    drug_id: UUID
    channel: str = "email"            # email | whatsapp


class ConfidenceBand(BaseModel):
    label: str       # "high" | "medium" | "low"
    threshold: float
    action: str


class GovernanceDecision(BaseModel):
    customer_id: UUID
    drug_id: UUID
    drug_name: str

    # ── من نموذج الدورة ──────────────────────────────────────────
    predicted_days: float
    cycle_confidence: float
    cycle_action: str                  # auto_send | human_review | cold_start

    # ── من نموذج الانقطاع ────────────────────────────────────────
    churn_probability: float
    churn_risk: str
    churn_action: str

    # ── القرار النهائي الموحَّد ────────────────────────────────────
    final_action: str
    final_action_reason: str

    # ── n8n Webhook ───────────────────────────────────────────────
    webhook_triggered: bool
    webhook_payload: Optional[dict] = None

    message: str
