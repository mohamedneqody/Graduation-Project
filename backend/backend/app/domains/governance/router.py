from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database.session import get_db
from . import schemas, service

router = APIRouter()
internal_router = APIRouter()


# ── Public API (الواجهة الأمامية / Dashboard) ────────────────────────────

@router.post(
    "/evaluate",
    response_model=schemas.GovernanceDecision,
    summary="تقييم قرار التذكير بناءً على Confidence (FR-07 + FR-08)",
    description="""
**Confidence-Based Governance Engine — Pull Pattern (SAD §6.4)**

يأخذ تنبؤات النموذجين ويحوّلها لإجراء تشغيلي مُسجَّل:

| الـ Confidence | القرار | ما يحدث |
|---|---|---|
| > 80% | `auto_send` | يُسجَّل في `pending_reminders` → n8n يُرسِل |
| 50-80% | `human_review` | يُسجَّل في `pending_reminders` → مراجعة بشرية |
| < 50% | `cold_start` | لا يُسجَّل — بيانات غير كافية |

> **ملاحظة معمارية:** n8n هو المُحرِّك الذي يـ poll `/internal/governance/pending`
> كل صباح ويُرسِل التذكيرات. FastAPI هو المصدر فقط.
""",
)
async def evaluate_governance(
    body: schemas.GovernanceRequest,
    db: AsyncSession = Depends(get_db),
):
    return await service.evaluate_governance(
        customer_id=body.customer_id,
        drug_id=body.drug_id,
        channel=body.channel,
        db=db,
    )


@router.get(
    "/thresholds",
    summary="عرض عتبات الثقة المُعتمَدة",
)
async def get_thresholds():
    """يُرجع العتبات الحالية المُستخدَمة في قرارات الحوكمة."""
    return {
        "pattern": "pull",
        "description": "n8n يـ poll /internal/governance/pending (SAD §6.4)",
        "thresholds": [
            {"label": "high",   "min": 0.80, "max": 1.00, "action": "auto_send",    "queued": True,  "description": "يُسجَّل في pending_reminders → n8n يُرسِل"},
            {"label": "medium", "min": 0.50, "max": 0.80, "action": "human_review", "queued": True,  "description": "يُسجَّل في pending_reminders → مراجعة بشرية"},
            {"label": "low",    "min": 0.00, "max": 0.50, "action": "cold_start",   "queued": False, "description": "لا يُسجَّل — بيانات غير كافية"},
        ],
        "churn_override": {
            "threshold": 0.70,
            "action": "human_review",
            "description": "Churn > 70% يُجبر على human_review بغض النظر عن Confidence",
        },
    }


# ── Internal API (n8n فقط) ───────────────────────────────────────────────

@internal_router.get(
    "/pending",
    summary="[n8n] قراءة التذكيرات المنتظرة",
    description="""
**Internal endpoint — يُستدعى من n8n فقط.**

يُرجع جميع السجلات بحالة `pending` مع بيانات العميل والدواء.
n8n يقرأ هذا كل صباح، يُرسِل، ثم يُحدِّث الحالة عبر `PATCH /{id}/status`.
""",
)
async def get_pending_reminders(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_pending_reminders(db, limit=limit)


@internal_router.patch(
    "/{reminder_id}/status",
    summary="[n8n] تحديث حالة التذكير بعد الإرسال",
    description="n8n يستدعيه بعد إرسال التذكير. القيم المقبولة: `sent` | `failed`.",
)
async def update_reminder_status(
    reminder_id: UUID = Path(..., description="reminder_id من جدول pending_reminders"),
    status: str = Query(..., description="sent | failed"),
    db: AsyncSession = Depends(get_db),
):
    if status not in ("sent", "failed"):
        return {"error": "status يجب أن يكون 'sent' أو 'failed'"}
    return await service.update_reminder_status(reminder_id, status, db)


@internal_router.patch(
    "/{reminder_id}/approve",
    summary="[Pharmacy Staff] Approve human_review",
    description="Changes decision from human_review to auto_send.",
)
async def approve_human_review(
    reminder_id: UUID = Path(..., description="reminder_id"),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    result = await db.execute(
        text("""
            UPDATE pending_reminders
            SET decision = 'auto_send'
            WHERE reminder_id = :rid AND decision = 'human_review' AND status = 'pending'
            RETURNING reminder_id, decision
        """),
        {"rid": str(reminder_id)}
    )
    row = result.first()
    await db.commit()
    if not row:
        return {"error": "Record not found or not in human_review state"}
    return {"message": "Approved", "reminder_id": str(row.reminder_id), "decision": row.decision}

