"""
Confidence-Based Governance Service (FR-07 + FR-08)
════════════════════════════════════════════════════════════════════════════
النمط المعتمَد (أ) — Pull Pattern: موثَّق في SAD §6.4
  FastAPI = المصدر  |  n8n = المُحرِّك

  1. FastAPI يُقيِّم التنبؤات ويُسجِّل القرار في pending_reminders
  2. n8n يـ poll  GET /internal/governance/pending كل صباح
  3. n8n يُرسِل التذكيرات ثم يُحدِّث الحالة عبر PATCH /internal/governance/{id}/status

عتبات الثقة (FR-07):
  confidence > 0.80  →  auto_send    (يُسجَّل في pending_reminders)
  0.50 ≤ conf ≤ 0.80 →  human_review (يُسجَّل كـ human_review للمراجعة)
  confidence < 0.50  →  cold_start   (لا يُسجَّل — بيانات غير كافية)

قاعدة Churn Override:
  Churn > 0.70 → human_review بغض النظر عن cycle confidence
════════════════════════════════════════════════════════════════════════════
"""
import uuid
from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drug import Drug
from app.models.tracking import PendingReminder
from app.domains.prediction.service import predict_cycle, predict_churn
from app.core.config import settings

# ── عتبات الثقة (FR-07) ─────────────────────────────────────────────────
THRESHOLD_HIGH   = 0.80   # auto_send
THRESHOLD_MEDIUM = 0.50   # human_review
CHURN_CONCERN    = 0.70   # Churn override إلى human_review


# ── حساب الإجراء بناءً على Confidence ───────────────────────────────────

def _decide_action(confidence: float, churn_prob: float) -> tuple[str, str]:
    """يُرجع (action, reason)."""
    if churn_prob >= CHURN_CONCERN:
        return "human_review", f"Churn risk مرتفع ({churn_prob:.0%}) — يحتاج مراجعة بشرية قبل الإرسال"
    if confidence >= THRESHOLD_HIGH:
        return "auto_send", f"Confidence {confidence:.0%} ≥ 80% — يُسجَّل في pending_reminders لـ n8n"
    if confidence >= THRESHOLD_MEDIUM:
        return "human_review", f"Confidence {confidence:.0%} في النطاق 50-80% — يحتاج موافقة بشرية"
    return "cold_start", f"Confidence {confidence:.0%} < 50% — بيانات غير كافية، لا تذكير"


# ── الخدمة الرئيسية ──────────────────────────────────────────────────────

async def evaluate_governance(
    customer_id: uuid.UUID,
    drug_id: uuid.UUID,
    channel: str,
    db: AsyncSession,
) -> dict:
    """
    النمط (أ) — Pull:
    1. يستدعي نموذجي ML (Cycle + Churn)
    2. يُطبِّق عتبات الثقة
    3. لو auto_send أو human_review → يُسجِّل في pending_reminders
    4. يُسجِّل في AuditLog
    5. n8n يـ poll pending_reminders ويُرسِل بشكل مستقل
    """
    # 1. تنبؤات ML
    cycle_result = await predict_cycle(db, customer_id, drug_id)
    churn_result = await predict_churn(db, customer_id, drug_id)

    cycle_conf = cycle_result.confidence
    churn_prob = churn_result.churn_probability

    # 2. القرار
    final_action, final_reason = _decide_action(cycle_conf, churn_prob)

    # قرار الـ Churn منفرداً (للعرض)
    churn_action = "human_review" if churn_prob >= 0.50 else "auto_send"

    # 3. اسم الدواء
    drug_row = (await db.execute(select(Drug).where(Drug.drug_id == drug_id))).scalar_one_or_none()
    drug_name = drug_row.name if drug_row else str(drug_id)

    # 4. تسجيل في pending_reminders (فقط لو auto_send أو human_review)
    reminder_id = None
    queued = False
    if final_action in ("auto_send", "human_review"):
        pending = PendingReminder(
            customer_id=customer_id,
            drug_id=drug_id,
            channel=channel,
            decision=final_action,
            cycle_confidence=cycle_conf,
            churn_probability=churn_prob,
            predicted_days=cycle_result.predicted_days,
            status="pending",
        )
        db.add(pending)
        await db.flush()  # يحصل على الـ ID قبل commit
        reminder_id = str(pending.reminder_id)
        queued = True

    # 5. تسجيل في AuditLog
    await db.execute(
        text("""
            INSERT INTO audit_logs (log_id, tenant_id, actor_id, action_type, target_entity)
            SELECT
                gen_random_uuid(),
                c.tenant_id,
                :actor,
                :action_type,
                :target
            FROM customers c
            WHERE c.customer_id = :cid
        """),
        {
            "actor": "governance_engine",
            "action_type": f"governance_{final_action}",
            "target": f"drug:{drug_id}",
            "cid": str(customer_id),
        },
    )
    await db.commit()

    return {
        "customer_id": customer_id,
        "drug_id": drug_id,
        "drug_name": drug_name,
        "predicted_days": cycle_result.predicted_days,
        "cycle_confidence": cycle_conf,
        "cycle_action": final_action,
        "churn_probability": churn_prob,
        "churn_risk": churn_result.churn_risk,
        "churn_action": churn_action,
        "final_action": final_action,
        "final_action_reason": final_reason,
        # ── Pull Pattern fields (يستبدل webhook_triggered) ──────────────
        "webhook_triggered": False,          # لا push — n8n يـ poll
        "webhook_payload": None,             # لا payload — يُرسَل عبر n8n poll
        "reminder_queued": queued,
        "reminder_id": reminder_id,
        "n8n_poll_endpoint": "/internal/governance/pending",
        "message": _action_message(final_action, drug_name, cycle_result.predicted_days),
    }


async def get_pending_reminders(db: AsyncSession, limit: int = 100) -> list:
    """
    n8n يستدعي هذا الـ endpoint كل صباح (pull).
    يُرجع السجلات بحالة 'pending' + معلومات العميل والدواء.
    """
    rows = await db.execute(
        text("""
            SELECT
                pr.reminder_id,
                pr.customer_id,
                c.full_name  AS customer_name,
                c.phone      AS customer_phone,
                c.email      AS customer_email,
                pr.drug_id,
                d.name       AS drug_name,
                pr.channel,
                pr.decision,
                pr.cycle_confidence,
                pr.churn_probability,
                pr.predicted_days,
                pr.status,
                pr.created_at
            FROM pending_reminders pr
            JOIN customers c ON c.customer_id = pr.customer_id
            JOIN drugs     d ON d.drug_id     = pr.drug_id
            WHERE pr.status = 'pending'
            ORDER BY pr.created_at ASC
            LIMIT :limit
        """),
        {"limit": limit},
    )
    return [dict(r._mapping) for r in rows.all()]


async def update_reminder_status(
    reminder_id: uuid.UUID,
    status: str,
    db: AsyncSession,
) -> dict:
    """
    n8n يستدعي هذا بعد إرسال التذكير لتحديث الحالة (sent | failed).
    """
    result = await db.execute(
        text("""
            UPDATE pending_reminders
            SET status = :status, processed_at = NOW()
            WHERE reminder_id = :rid
            RETURNING reminder_id, status, processed_at
        """),
        {"status": status, "rid": str(reminder_id)},
    )
    row = result.first()
    await db.commit()
    if not row:
        return {"error": f"reminder_id {reminder_id} not found"}
    return dict(row._mapping)


def _action_message(action: str, drug_name: str, days: float) -> str:
    if action == "auto_send":
        return f"✅ '{drug_name}' سيُرسَل تذكيره عبر n8n خلال {days:.0f} يوم (pending_reminders)."
    if action == "human_review":
        return f"⏸️ '{drug_name}' بانتظار مراجعة بشرية — مُسجَّل في pending_reminders."
    return f"⛔ '{drug_name}' — بيانات غير كافية، لم يُضَف لقائمة التذكيرات."
