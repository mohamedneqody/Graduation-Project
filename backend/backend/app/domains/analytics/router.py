"""
Analytics Router — Dashboard KPIs (FR-09) + A/B Testing (FR-13) + Weekly Summary (FR-15)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database.session import get_db
from . import schemas, service

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# FR-09 — Dashboard KPIs (لحظي)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/summary",
    response_model=schemas.DashboardSummary,
    summary="[FR-09] مؤشرات الأداء الرئيسية (Dashboard) — لحظي",
)
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """
    يُرجع KPIs الـ Dashboard بشكل لحظي (PRD §10):
    - **العملاء**: الإجمالي + معدل النشاط 30 يوماً
    - **الطلبات**: الإجمالي + الإيراد + متوسط قيمة الطلب + آخر 7 أيام
    - **ML**: MAE النموذج + إجمالي الدورات
    - **أعلى 5 فئات دوائية** بالطلبات والإيراد
    """
    return await service.get_dashboard_summary(db)


# ═══════════════════════════════════════════════════════════════════════════════
# FR-13 — A/B Testing
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/ab-tests",
    response_model=schemas.ABTestOut,
    status_code=201,
    summary="[FR-13] إنشاء تجربة A/B جديدة",
)
async def create_ab_test(
    data: schemas.ABTestCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    ينشئ تجربة A/B لاختبار نمطَي رسالة (مثال: discount vs plain).

    **الـ Variants:** variant_a و variant_b (الاسم الذي يُرسَل لـ n8n في `ab_variant`).
    """
    return await service.create_ab_test(db, data)


@router.get(
    "/ab-tests",
    response_model=list[schemas.ABTestOut],
    summary="[FR-13] قائمة تجارب A/B",
)
async def list_ab_tests(db: AsyncSession = Depends(get_db)):
    """يُرجع جميع تجارب A/B مرتبةً بالأحدث."""
    return await service.list_ab_tests(db)


@router.get(
    "/ab-tests/{test_id}/summary",
    response_model=schemas.ABTestSummary,
    summary="[FR-13] نتائج تجربة A/B",
)
async def get_ab_test_summary(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    يُرجع معدل التحوّل لكل variant + اسم الفائز (إن كانت البيانات كافية).

    الفائز يُحدَّد عند وجود ≥10 رسائل لكل variant وفارق ≥2% في معدل التحوّل.
    """
    try:
        return await service.get_ab_test_summary(db, test_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/ab-tests/record-result",
    summary="[FR-13][n8n] تسجيل نتيجة رسالة A/B",
)
async def record_ab_result(
    data: schemas.RecordABResultIn,
    db: AsyncSession = Depends(get_db),
):
    """
    **Internal — يُستدعى من n8n** بعد إرسال رسالة ضمن تجربة A/B.
    يُسجّل الـ variant المُستخدَم في `ab_test_results`.
    """
    return await service.record_ab_result(db, data)


@router.post(
    "/ab-tests/mark-converted",
    summary="[FR-13][n8n] تسجيل تحوّل عميل (اشترى بعد الرسالة)",
)
async def mark_converted(
    data: schemas.MarkConvertedIn,
    db: AsyncSession = Depends(get_db),
):
    """
    **Internal — يُستدعى من n8n** عند رصد طلب جديد بعد رسالة A/B.
    يُحدِّث `converted = TRUE` في `ab_test_results`.
    """
    return await service.mark_converted(db, data.notification_id)


# ═══════════════════════════════════════════════════════════════════════════════
# FR-15 — Weekly Executive Summary (لـ n8n + صاحب المتجر)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/weekly-summary",
    summary="[FR-15][n8n] الملخص الأسبوعي لصاحب المتجر",
)
async def get_weekly_summary(db: AsyncSession = Depends(get_db)):
    """
    **يُستدعى من n8n كل صباح أحد** ثم يُرسَل لصاحب المتجر عبر واتساب.

    يُغطي آخر 7 أيام:
    - الطلبات والإيراد
    - التذكيرات: مُرسَلة / منتظرة / فاشلة / تحتاج مراجعة
    - أعلى دواء مبيعاً
    - نتائج A/B التراكمية للأسبوع
    """
    return await service.get_weekly_summary(db)
