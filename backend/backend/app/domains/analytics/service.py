"""
Analytics Service — Dashboard KPIs (FR-09) + A/B Testing (FR-13) + Weekly Summary (FR-15)
"""
from datetime import datetime, timezone, timedelta, date
from typing import Optional
import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, text

from app.models.order import Order, OrderItem
from app.models.customer import Customer
from app.models.drug import Drug
from app.models.tracking import CustomerCycle
from app.models.ab_test import ABTest, ABTestResult
from . import schemas

# ── MAE من آخر تدريب (Optuna XGBoost) — يُحدَّث بعد كل إعادة تدريب ─────────
REGRESSION_MAE_DAYS: float = 3.27


# ═══════════════════════════════════════════════════════════════════════════════
# FR-09 — Dashboard KPIs
# ═══════════════════════════════════════════════════════════════════════════════

async def get_dashboard_summary(db: AsyncSession) -> schemas.DashboardSummary:
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago  = now - timedelta(days=7)

    # 1. إجمالي العملاء
    total_customers: int = (
        await db.execute(select(func.count()).select_from(Customer))
    ).scalar_one()

    # 2. العملاء النشطون في 30 يوم الأخيرة
    active_sq = (
        select(Order.customer_id)
        .where(Order.order_date >= thirty_days_ago, Order.status == "completed")
        .distinct()
        .subquery()
    )
    active_customers_30d: int = (
        await db.execute(select(func.count()).select_from(active_sq))
    ).scalar_one()

    activity_rate = round(active_customers_30d / total_customers * 100, 1) if total_customers else 0.0

    # 3. إجمالي الطلبات
    total_orders: int = (
        await db.execute(
            select(func.count(Order.order_id)).where(Order.status == "completed")
        )
    ).scalar_one()

    # 4. طلبات آخر 7 أيام
    orders_last_7d: int = (
        await db.execute(
            select(func.count(Order.order_id)).where(
                Order.status == "completed",
                Order.order_date >= seven_days_ago,
            )
        )
    ).scalar_one()

    # 5. إجمالي الإيراد
    revenue_raw = (
        await db.execute(
            select(func.sum(OrderItem.price * OrderItem.quantity))
            .join(Order, OrderItem.order_id == Order.order_id)
            .where(Order.status == "completed")
        )
    ).scalar_one()
    total_revenue = float(revenue_raw or 0)
    avg_order_value = round(total_revenue / total_orders, 2) if total_orders else 0.0

    # 6. إجمالي الدورات المُتتبَّعة
    total_cycles: int = (
        await db.execute(select(func.count()).select_from(CustomerCycle))
    ).scalar_one()

    # 7. توزيع أعلى 5 فئات دوائية
    cat_rows = (
        await db.execute(
            select(
                Drug.category,
                func.count(OrderItem.order_item_id).label("order_count"),
                func.sum(OrderItem.price * OrderItem.quantity).label("revenue"),
            )
            .join(OrderItem, Drug.drug_id == OrderItem.drug_id)
            .join(Order, OrderItem.order_id == Order.order_id)
            .where(Order.status == "completed")
            .group_by(Drug.category)
            .order_by(desc("order_count"))
            .limit(5)
        )
    ).all()

    top_categories = [
        schemas.CategoryBreakdown(
            category=row.category or "Unknown",
            order_count=row.order_count,
            revenue=round(float(row.revenue or 0), 2),
            percentage=round(row.order_count / total_orders * 100, 1) if total_orders else 0.0,
        )
        for row in cat_rows
    ]

    return schemas.DashboardSummary(
        total_customers=total_customers,
        active_customers_30d=active_customers_30d,
        activity_rate_pct=activity_rate,
        total_orders=total_orders,
        total_revenue=round(total_revenue, 2),
        avg_order_value=avg_order_value,
        orders_last_7d=orders_last_7d,
        regression_model_mae_days=REGRESSION_MAE_DAYS,
        total_cycles_tracked=total_cycles,
        top_drug_categories=top_categories,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# FR-13 — A/B Testing
# ═══════════════════════════════════════════════════════════════════════════════

async def create_ab_test(db: AsyncSession, data: schemas.ABTestCreate) -> ABTest:
    """إنشاء تجربة A/B جديدة."""
    test = ABTest(
        tenant_id=data.tenant_id,
        test_name=data.test_name,
        variant_a=data.variant_a,
        variant_b=data.variant_b,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    db.add(test)
    await db.commit()
    await db.refresh(test)
    return test


async def list_ab_tests(db: AsyncSession) -> list[ABTest]:
    """قائمة كل التجارب."""
    result = await db.execute(select(ABTest).order_by(ABTest.created_at.desc()))
    return list(result.scalars().all())


async def get_ab_test_summary(db: AsyncSession, test_id: uuid.UUID) -> schemas.ABTestSummary:
    """
    احسب معدل التحوّل لكل variant.
    يعتمد على ab_test_results المرتبطة بالـ test_id.
    """
    test = (await db.execute(select(ABTest).where(ABTest.test_id == test_id))).scalar_one_or_none()
    if not test:
        raise ValueError(f"ab_test {test_id} not found")

    rows = (
        await db.execute(
            select(
                ABTestResult.variant,
                func.count(ABTestResult.result_id).label("sent_count"),
                func.sum(ABTestResult.converted.cast(sa.Integer)).label("converted_count"),
            )
            .where(ABTestResult.test_id == test_id)
            .group_by(ABTestResult.variant)
        )
    ).all()

    stats_map: dict[str, schemas.ABTestVariantStats] = {}
    for row in rows:
        sent = row.sent_count or 0
        converted = int(row.converted_count or 0)
        stats_map[row.variant] = schemas.ABTestVariantStats(
            variant=row.variant,
            sent_count=sent,
            converted_count=converted,
            conversion_rate_pct=round(converted / sent * 100, 1) if sent else 0.0,
        )

    def _empty(v: str) -> schemas.ABTestVariantStats:
        return schemas.ABTestVariantStats(variant=v, sent_count=0, converted_count=0, conversion_rate_pct=0.0)

    a_stats = stats_map.get(test.variant_a, _empty(test.variant_a))
    b_stats = stats_map.get(test.variant_b, _empty(test.variant_b))

    # تحديد الفائز (يحتاج حدًا أدنى 10 رسالة لكل variant)
    winner: Optional[str] = None
    if a_stats.sent_count >= 10 and b_stats.sent_count >= 10:
        if a_stats.conversion_rate_pct > b_stats.conversion_rate_pct + 2:
            winner = "A"
        elif b_stats.conversion_rate_pct > a_stats.conversion_rate_pct + 2:
            winner = "B"
        else:
            winner = "tie"

    return schemas.ABTestSummary(
        test_id=test.test_id,
        test_name=test.test_name,
        is_active=test.is_active,
        variant_a_stats=a_stats,
        variant_b_stats=b_stats,
        winner=winner,
    )


async def record_ab_result(db: AsyncSession, data: schemas.RecordABResultIn) -> dict:
    """n8n يُسجِّل هنا كل رسالة أُرسلت ضمن تجربة A/B."""
    result = ABTestResult(
        test_id=data.test_id,
        notification_id=data.notification_id,
        variant=data.variant,
    )
    db.add(result)
    await db.commit()
    return {"status": "recorded", "result_id": str(result.result_id)}


async def mark_converted(db: AsyncSession, notification_id: uuid.UUID) -> dict:
    """
    n8n يُعلِّم هنا بأن العميل اشترى بعد رسالة A/B.
    يُحدِّث أول result_id مرتبط بهذا الـ notification_id.
    """
    await db.execute(
        text("""
            UPDATE ab_test_results
            SET converted = TRUE
            WHERE notification_id = :nid
        """),
        {"nid": str(notification_id)},
    )
    await db.commit()
    return {"status": "marked_converted", "notification_id": str(notification_id)}


# ═══════════════════════════════════════════════════════════════════════════════
# FR-15 — Weekly Executive Summary (لـ n8n)
# ═══════════════════════════════════════════════════════════════════════════════

async def get_weekly_summary(db: AsyncSession) -> dict:
    """
    ملخص أسبوعي كامل يستدعيه n8n كل صباح أحد ثم يُرسله لصاحب المتجر عبر واتساب.

    يُغطي:
    - الطلبات والإيراد في الأسبوع الماضي
    - عدد التذكيرات المُرسَلة والمُحوَّلة
    - عدد التذكيرات بانتظار مراجعة بشرية
    - أعلى دواء مبيعاً هذا الأسبوع
    - نتيجة A/B إجمالية (لو هناك تجارب نشطة)
    """
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # 1. الطلبات والإيراد هذا الأسبوع
    orders_row = (
        await db.execute(
            select(
                func.count(Order.order_id).label("count"),
                func.sum(OrderItem.price * OrderItem.quantity).label("revenue"),
            )
            .join(OrderItem, OrderItem.order_id == Order.order_id)
            .where(Order.status == "completed", Order.order_date >= week_ago)
        )
    ).one()
    weekly_orders   = orders_row.count or 0
    weekly_revenue  = float(orders_row.revenue or 0)

    # 2. التذكيرات (pending_reminders)
    reminders = (
        await db.execute(
            text("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'sent')    AS sent_count,
                    COUNT(*) FILTER (WHERE status = 'pending') AS pending_count,
                    COUNT(*) FILTER (WHERE status = 'failed')  AS failed_count,
                    COUNT(*) FILTER (WHERE decision = 'human_review' AND status = 'pending') AS awaiting_review
                FROM pending_reminders
                WHERE created_at >= :week_ago
            """),
            {"week_ago": week_ago},
        )
    ).one()

    # 3. أعلى دواء مبيعاً
    top_drug_row = (
        await db.execute(
            select(Drug.name, func.sum(OrderItem.quantity).label("qty"))
            .join(OrderItem, Drug.drug_id == OrderItem.drug_id)
            .join(Order, OrderItem.order_id == Order.order_id)
            .where(Order.status == "completed", Order.order_date >= week_ago)
            .group_by(Drug.name)
            .order_by(desc("qty"))
            .limit(1)
        )
    ).first()

    # 4. نتائج A/B (إجمالي خلال الأسبوع)
    ab_row = (
        await db.execute(
            text("""
                SELECT
                    variant,
                    COUNT(*) AS sent,
                    SUM(converted::int) AS converted
                FROM ab_test_results
                WHERE created_at >= :week_ago
                GROUP BY variant
            """),
            {"week_ago": week_ago},
        )
    ).all()
    ab_summary = [
        {"variant": r.variant, "sent": r.sent, "converted": r.converted or 0,
         "conversion_pct": round((r.converted or 0) / r.sent * 100, 1) if r.sent else 0}
        for r in ab_row
    ]

    return {
        "period": f"{week_ago.date()} → {now.date()}",
        "orders": {
            "count":   weekly_orders,
            "revenue": round(weekly_revenue, 2),
        },
        "reminders": {
            "sent":            reminders.sent_count    or 0,
            "pending":         reminders.pending_count or 0,
            "failed":          reminders.failed_count  or 0,
            "awaiting_review": reminders.awaiting_review or 0,
        },
        "top_drug_this_week": {
            "name":     top_drug_row.name if top_drug_row else None,
            "quantity": int(top_drug_row.qty) if top_drug_row else 0,
        },
        "ab_test_summary": ab_summary,
        "generated_at": now.isoformat(),
    }
